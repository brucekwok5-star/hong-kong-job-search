#!/usr/bin/env python3
"""
Manual Job Search Helper - Full Version
Features:
- GUI Interface (Tkinter)
- Open 3 browser tabs
- Auto-parse raw job content
- Duplicate Detection
- Google Sheets Export
- Multi-format Export (CSV, JSON, Excel)
- Job Stats Dashboard
- Search History
- Filter/Sort
- Custom Skills
"""

import os
import sys
import json
import csv
import re
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

# GUI imports
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

# Google Sheets imports
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSHEETS_AVAILABLE = True
except ImportError:
    GSHEETS_AVAILABLE = False

# Excel export
try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

# ============== CONFIGURATION ==============
SEARCH_URLS = [
    ("Indeed", "https://hk.indeed.com/jobs?q=(jenkins+AND+devops)+AND+(lead+or+manager)&l=Hong+Kong&fromage=7"),
    ("eFinancialCareers", "https://www.efinancialcareers.hk/jobs/(jenkins-and-devops)-and-(lead-or-manager-or-senior)/in-hong-kong"),
    ("JobsDB", "https://hk.jobsdb.com/(jenkins-AND-devops)-AND-(lead-AND-senior-AND-manager)-jobs/in-Hong-Kong-SAR?daterange=7")
]

DEFAULT_SKILLS = [
    "Kubernetes", "K8S", "Jenkins", "Docker", "Terraform", "Ansible",
    "AWS", "Azure", "GCP", "Google Cloud", "Python", "Java", "NodeJS",
    "Git", "GitLab", "GitHub", "Bitbucket", "SonarQube", "Chef", "Puppet",
    "ArgoCD", "Linux", "Unix", "DevOps", "DevSecOps", "CI/CD", "Pipeline",
    "Cloud", "Splunk", "MongoDB", "Oracle", "NoSQL", "Redis", "Microservices"
]

DATA_DIR = Path("job_data")
HISTORY_FILE = DATA_DIR / "history.json"
SKILLS_FILE = DATA_DIR / "custom_skills.json"

# ============== DATA MANAGEMENT ==============

class Job:
    def __init__(self, title, company, source="", skills=None, posted_date="", link="", location="Hong Kong"):
        self.title = title
        self.company = company
        self.source = source
        self.skills = skills or []
        self.posted_date = posted_date
        self.link = link
        self.location = location
        self.added_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    def to_dict(self):
        return {
            "title": self.title,
            "company": self.company,
            "source": self.source,
            "skills": self.skills,
            "posted_date": self.posted_date,
            "link": self.link,
            "location": self.location,
            "added_date": self.added_date
        }

    @staticmethod
    def from_dict(d):
        return Job(
            d.get("title", ""),
            d.get("company", ""),
            d.get("source", ""),
            d.get("skills", []),
            d.get("posted_date", ""),
            d.get("link", ""),
            d.get("location", "Hong Kong")
        )

    def __eq__(self, other):
        return self.title == other.title and self.company == other.company

    def __hash__(self):
        return hash((self.title, self.company))


class JobManager:
    def __init__(self):
        self.jobs = []
        self.history = []
        self.custom_skills = DEFAULT_SKILLS.copy()
        self.load_data()

    def load_data(self):
        """Load history and custom skills"""
        DATA_DIR.mkdir(exist_ok=True)

        # Load custom skills
        if SKILLS_FILE.exists():
            with open(SKILLS_FILE, 'r') as f:
                self.custom_skills = json.load(f)

        # Load history
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, 'r') as f:
                data = json.load(f)
                for session in data:
                    jobs = [Job.from_dict(j) for j in session.get("jobs", [])]
                    self.history.append({
                        "date": session.get("date", ""),
                        "jobs": jobs
                    })

    def save_history(self):
        """Save job history"""
        data = []
        if self.history:
            for session in self.history[-30:]:  # Keep last 30 sessions
                data.append({
                    "date": session["date"],
                    "jobs": [j.to_dict() for j in session["jobs"]]
                })

        with open(HISTORY_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def save_custom_skills(self):
        """Save custom skills list"""
        with open(SKILLS_FILE, 'w') as f:
            json.dump(self.custom_skills, f, indent=2)

    def add_job(self, job):
        """Add job with duplicate detection"""
        # Check for duplicates
        for existing in self.jobs:
            if existing.title.lower() == job.title.lower() and \
               existing.company.lower() == job.company.lower():
                return False, "Duplicate job not added"

        self.jobs.append(job)
        return True, "Job added successfully"

    def add_jobs_from_text(self, text, source_hint=""):
        """Auto-parse raw text and add jobs"""
        added_count = 0
        jobs_data = self._parse_raw_text(text, source_hint)

        for job_data in jobs_data:
            job = Job(**job_data)
            success, msg = self.add_job(job)
            if success:
                added_count += 1

        # Save to history
        if added_count > 0:
            self.history.append({
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "jobs": [j for j in self.jobs[-added_count:]]
            })
            self.save_history()

        return added_count

    def _parse_raw_text(self, text, source_hint=""):
        """Parse raw job content into structured data"""
        jobs = []

        # Detect source
        source = source_hint
        if 'indeed' in text.lower():
            source = 'Indeed'
        elif 'efinancialcareers' in text.lower():
            source = 'eFinancialCareers'
        elif 'jobsdb' in text.lower():
            source = 'JobsDB'

        # Extract job title
        title_match = re.search(r'(?:Job title:)?\s*([A-Z][^\n]{10,80})', text)
        title = title_match.group(1).strip() if title_match else "Unknown Title"

        # Extract company
        company_match = re.search(r'(?:Company|Client|Employer|Pte\.? Ltd\.?|Limited|HK):?\s*([^\n]{3,50})', text, re.IGNORECASE)
        if not company_match:
            company_match = re.search(r'([A-Z][^\n]{3,40} (?:Limited|Pte\.? Ltd\.?|Ltd\.?|HK))', text)
        company = company_match.group(1).strip() if company_match else "Unknown Company"

        # Extract posted date
        date_match = re.search(r'Posted\s*(\d+[hdwmy]\s*ago|Today|Yesterday)', text, re.IGNORECASE)
        posted_date = date_match.group(1).strip() if date_match else ""

        # Extract skills
        found_skills = []
        for skill in self.custom_skills:
            if re.search(r'\b' + re.escape(skill) + r'\b', text, re.IGNORECASE):
                found_skills.append(skill)

        # Extract link
        link_match = re.search(r'(https?://[^\s<>"]+)', text)
        link = link_match.group(1).strip() if link_match else ""

        jobs.append({
            "title": title,
            "company": company,
            "source": source,
            "skills": list(set(found_skills)),
            "posted_date": posted_date,
            "link": link,
            "location": "Hong Kong"
        })

        return jobs

    def get_stats(self):
        """Get job statistics"""
        if not self.jobs:
            return {}

        # Count by source
        source_count = {}
        # Count by skills
        skill_count = {}

        for job in self.jobs:
            source_count[job.source] = source_count.get(job.source, 0) + 1
            for skill in job.skills:
                skill_count[skill] = skill_count.get(skill, 0) + 1

        return {
            "total": len(self.jobs),
            "by_source": source_count,
            "top_skills": sorted(skill_count.items(), key=lambda x: x[1], reverse=True)[:10]
        }

    def filter_jobs(self, source=None, keyword=None):
        """Filter jobs by source or keyword"""
        filtered = self.jobs

        if source and source != "All":
            filtered = [j for j in filtered if j.source == source]

        if keyword:
            keyword = keyword.lower()
            filtered = [j for j in filtered
                       if keyword in j.title.lower() or
                          keyword in j.company.lower() or
                          any(keyword in s.lower() for s in j.skills)]

        return filtered

    def sort_jobs(self, jobs, sort_by="date"):
        """Sort jobs"""
        if sort_by == "title":
            return sorted(jobs, key=lambda j: j.title)
        elif sort_by == "company":
            return sorted(jobs, key=lambda j: j.company)
        elif sort_by == "source":
            return sorted(jobs, key=lambda j: j.source)
        else:
            return sorted(jobs, key=lambda j: j.added_date, reverse=True)

    def export_csv(self, filepath):
        """Export to CSV"""
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Job Title", "Company", "Source", "Key Skills", "Posted Date", "Link", "Location", "Added Date"])
            for job in self.jobs:
                writer.writerow([
                    job.title, job.company, job.source,
                    ", ".join(job.skills), job.posted_date,
                    job.link, job.location, job.added_date
                ])
        return filepath

    def export_json(self, filepath):
        """Export to JSON"""
        with open(filepath, 'w', encoding='utf-8') as f:
            data = [j.to_dict() for j in self.jobs]
            json.dump(data, f, indent=2)
        return filepath

    def export_excel(self, filepath):
        """Export to Excel"""
        if not EXCEL_AVAILABLE:
            return None

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Jobs"

        # Headers
        headers = ["Job Title", "Company", "Source", "Key Skills", "Posted Date", "Link", "Location", "Added Date"]
        ws.append(headers)

        # Data
        for job in self.jobs:
            ws.append([
                job.title, job.company, job.source,
                ", ".join(job.skills), job.posted_date,
                job.link, job.location, job.added_date
            ])

        wb.save(filepath)
        return filepath

    def export_google_sheets(self, spreadsheet_name="Hong Kong Job Search"):
        """Export to Google Sheets"""
        if not GSHEETS_AVAILABLE:
            return None, "gspread not installed"

        try:
            # Try to load credentials
            scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            credentials = Credentials.from_service_account_file('credentials.json', scopes=scopes)
            gc = gspread.authorize(credentials)

            # Create or open spreadsheet
            try:
                sh = gc.open(spreadsheet_name)
            except:
                sh = gc.create(spreadsheet_name)

            # Get first worksheet
            ws = sh.sheet1

            # Clear and update
            ws.clear()
            ws.append_row(["Job Title", "Company", "Source", "Key Skills", "Posted Date", "Link", "Location", "Added Date"])

            for job in self.jobs:
                ws.append_row([
                    job.title, job.company, job.source,
                    ", ".join(job.skills), job.posted_date,
                    job.link, job.location, job.added_date
                ])

            return sh.url, "Exported to Google Sheets!"

        except FileNotFoundError:
            return None, "credentials.json not found"
        except Exception as e:
            return None, str(e)


# ============== GUI APPLICATION ==============

class JobSearchGUI:
    def __init__(self):
        self.manager = JobManager()
        self.root = tk.Tk()
        self.root.title("Hong Kong Job Search Helper")
        self.root.geometry("900x700")

        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface"""
        # Menu
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Browser Tabs", command=self.open_browser)
        file_menu.add_command(label="Open Text File", command=self.open_text_file)
        file_menu.add_separator()
        file_menu.add_command(label="Export CSV", command=lambda: self.export_data("csv"))
        file_menu.add_command(label="Export JSON", command=lambda: self.export_data("json"))
        file_menu.add_command(label="Export Excel", command=lambda: self.export_data("excel"))
        file_menu.add_command(label="Export Google Sheets", command=lambda: self.export_data("gsheets"))
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="View Stats", command=self.show_stats)
        tools_menu.add_command(label="Manage Skills", command=self.manage_skills)
        tools_menu.add_command(label="Clear All Jobs", command=self.clear_jobs)

        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Top buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=0, column=0, columnspan=2, pady=5)

        ttk.Button(btn_frame, text="🔍 Open Search Tabs", command=self.open_browser).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📝 Paste Jobs", command=self.open_text_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📊 View Stats", command=self.show_stats).pack(side=tk.LEFT, padx=5)

        # Filter frame
        filter_frame = ttk.LabelFrame(main_frame, text="Filter & Sort", padding="10")
        filter_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        ttk.Label(filter_frame, text="Source:").pack(side=tk.LEFT)
        self.source_var = tk.StringVar(value="All")
        source_combo = ttk.Combobox(filter_frame, textvariable=self.source_var, values=["All", "Indeed", "JobsDB", "eFinancialCareers"], state="readonly", width=15)
        source_combo.pack(side=tk.LEFT, padx=5)

        ttk.Label(filter_frame, text="Keyword:").pack(side=tk.LEFT, padx=10)
        self.keyword_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.keyword_var, width=20).pack(side=tk.LEFT)

        ttk.Label(filter_frame, text="Sort:").pack(side=tk.LEFT, padx=10)
        self.sort_var = tk.StringVar(value="date")
        sort_combo = ttk.Combobox(filter_frame, textvariable=self.sort_var, values=["date", "title", "company", "source"], state="readonly", width=10)
        sort_combo.pack(side=tk.LEFT, padx=5)

        ttk.Button(filter_frame, text="Apply", command=self.apply_filter).pack(side=tk.LEFT, padx=10)

        # Jobs table
        table_frame = ttk.LabelFrame(main_frame, text="Jobs", padding="10")
        table_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Treeview
        columns = ("title", "company", "source", "skills", "posted")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)

        self.tree.heading("title", text="Job Title")
        self.tree.heading("company", text="Company")
        self.tree.heading("source", text="Source")
        self.tree.heading("skills", text="Skills")
        self.tree.heading("posted", text="Posted")

        self.tree.column("title", width=250)
        self.tree.column("company", width=150)
        self.tree.column("source", width=80)
        self.tree.column("skills", width=200)
        self.tree.column("posted", width=80)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # Load existing jobs
        self.refresh_table()

    def open_browser(self):
        """Open browser tabs"""
        for name, url in SEARCH_URLS:
            subprocess.run(["open", url])
        self.status_var.set(f"Opened {len(SEARCH_URLS)} browser tabs")

    def open_text_file(self):
        """Open text file for pasting"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"job_details_{timestamp}.txt"
        filepath = DATA_DIR / filename

        template = f"""# PASTE RAW JOB CONTENT HERE
# The program will auto-parse: title, company, skills, date, link
# Run 'python3 manual_job_search.py --parse' after pasting
# Or use the GUI to paste directly below:

---

"""
        with open(filepath, 'w') as f:
            f.write(template)

        subprocess.run(["open", "-a", "TextEdit", str(filepath)])
        self.status_var.set(f"Opened {filename}")

    def refresh_table(self, jobs=None):
        """Refresh the jobs table"""
        # Clear table
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Use provided jobs or filter
        if jobs is None:
            jobs = self.manager.filter_jobs(
                self.source_var.get(),
                self.keyword_var.get()
            )
            jobs = self.manager.sort_jobs(jobs, self.sort_var.get())

        # Add to table
        for job in jobs:
            skills_str = ", ".join(job.skills[:5])
            if len(job.skills) > 5:
                skills_str += "..."
            self.tree.insert("", tk.END, values=(
                job.title[:40] + "..." if len(job.title) > 40 else job.title,
                job.company[:25] + "..." if len(job.company) > 25 else job.company,
                job.source,
                skills_str,
                job.posted_date
            ))

        self.status_var.set(f"Showing {len(jobs)} jobs (Total: {len(self.manager.jobs)})")

    def apply_filter(self):
        """Apply filter and refresh table"""
        self.refresh_table()

    def show_stats(self):
        """Show job statistics"""
        stats = self.manager.get_stats()

        if not stats:
            messagebox.showinfo("Stats", "No jobs to analyze")
            return

        msg = f"📊 Job Statistics\n\n"
        msg += f"Total Jobs: {stats['total']}\n\n"

        msg += "By Source:\n"
        for source, count in stats['by_source'].items():
            msg += f"  • {source}: {count}\n"

        msg += "\nTop Skills:\n"
        for skill, count in stats['top_skills'][:10]:
            msg += f"  • {skill}: {count}\n"

        messagebox.showinfo("Job Statistics", msg)

    def manage_skills(self):
        """Manage custom skills"""
        win = tk.Toplevel(self.root)
        win.title("Manage Skills")
        win.geometry("400x500")

        frame = ttk.Frame(win, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Custom Skills (one per line):").pack()

        text = tk.Text(frame, height=20, width=40)
        text.pack(fill=tk.BOTH, expand=True, pady=5)

        # Load current skills
        for skill in self.manager.custom_skills:
            text.insert(tk.END, skill + "\n")

        def save_skills():
            content = text.get("1.0", tk.END).strip()
            skills = [s.strip() for s in content.split("\n") if s.strip()]
            self.manager.custom_skills = skills
            self.manager.save_custom_skills()
            messagebox.showinfo("Saved", "Skills saved successfully!")
            win.destroy()

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Save", command=save_skills).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=win.destroy).pack(side=tk.LEFT, padx=5)

    def clear_jobs(self):
        """Clear all jobs"""
        if messagebox.askyesno("Confirm", "Clear all jobs? This cannot be undone."):
            self.manager.jobs = []
            self.refresh_table()
            self.status_var.set("All jobs cleared")

    def export_data(self, format_type):
        """Export data to various formats"""
        if not self.manager.jobs:
            messagebox.showwarning("No Data", "No jobs to export")
            return

        if format_type == "csv":
            filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
            if filepath:
                self.manager.export_csv(filepath)
                messagebox.showinfo("Exported", f"Saved to {filepath}")

        elif format_type == "json":
            filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
            if filepath:
                self.manager.export_json(filepath)
                messagebox.showinfo("Exported", f"Saved to {filepath}")

        elif format_type == "excel":
            if not EXCEL_AVAILABLE:
                messagebox.showerror("Error", "openpyxl not installed. Run: pip install openpyxl")
                return
            filepath = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
            if filepath:
                self.manager.export_excel(filepath)
                messagebox.showinfo("Exported", f"Saved to {filepath}")

        elif format_type == "gsheets":
            if not GSHEETS_AVAILABLE:
                messagebox.showerror("Error", "gspread not installed. Run: pip install gspread google-auth")
                return

            url, msg = self.manager.export_google_sheets()
            if url:
                messagebox.showinfo("Exported", f"{msg}\n\n{url}")
                subprocess.run(["open", url])
            else:
                messagebox.showerror("Error", msg)

    def run(self):
        """Run the GUI"""
        self.root.mainloop()


# ============== COMMAND LINE INTERFACE ==============

def open_browser_tabs():
    """Open browser tabs"""
    print("Opening browser tabs...")
    for name, url in SEARCH_URLS:
        subprocess.run(["open", url])
        print(f"  - {name}")
    print()


def open_text_file():
    """Open text file for pasting"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"job_details_{timestamp}.txt"
    filepath = os.path.abspath(filename)

    template = f"""# Job Details - Paste raw content here
# Run: python3 manual_job_search.py --parse

---

PASTE BELOW:

"""
    with open(filepath, 'w') as f:
        f.write(template)

    subprocess.run(["open", "-a", "TextEdit", filepath])
    print(f"Opened {filename}")


def parse_jobs():
    """Parse jobs from latest text file"""
    import glob

    files = glob.glob("job_details_*.txt")
    if not files:
        print("No job details file found.")
        return

    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    latest_file = files[0]

    print(f"Parsing: {latest_file}\n")

    with open(latest_file, 'r') as f:
        content = f.read()

    # Find paste section
    lines = content.split('\n')
    paste_started = False
    paste_content = []

    for line in lines:
        if line.startswith('---'):
            paste_started = True
            continue
        if paste_started and line.strip():
            paste_content.append(line)

    raw_text = '\n'.join(paste_content)

    if not raw_text.strip():
        print("No content found. Please paste job details in the text file.")
        return

    # Parse and display
    manager = JobManager()
    count = manager.add_jobs_from_text(raw_text)

    if count > 0:
        print(f"✅ Added {count} job(s)\n")

        # Show stats
        stats = manager.get_stats()
        print(f"Total jobs: {stats['total']}")
        print(f"By source: {stats['by_source']}")
        print(f"Top skills: {[s[0] for s in stats['top_skills'][:5]]}")

        # Export to CSV
        manager.export_csv("hong_kong_jobs.csv")
        print(f"\n📁 Saved to: hong_kong_jobs.csv")

        # Open CSV
        subprocess.run(["open", "-a", "TextEdit", "hong_kong_jobs.csv"])
    else:
        print("Could not parse jobs.")


def main():
    """Main entry point"""
    # Check for GUI mode
    if GUI_AVAILABLE and len(sys.argv) == 1:
        print("Starting GUI...")
        app = JobSearchGUI()
        app.run()
        return

    # Command line mode
    print("="*60)
    print("  Hong Kong Job Search Helper")
    print("="*60)
    print()

    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == "--parse":
            parse_jobs()

        elif arg == "--browse" or arg == "-b":
            open_browser_tabs()

        elif arg == "--paste" or arg == "-p":
            open_text_file()

        elif arg == "--stats":
            manager = JobManager()
            stats = manager.get_stats()
            if stats:
                print(f"Total Jobs: {stats['total']}")
                print("\nBy Source:")
                for source, count in stats['by_source'].items():
                    print(f"  {source}: {count}")
                print("\nTop Skills:")
                for skill, count in stats['top_skills'][:10]:
                    print(f"  {skill}: {count}")
            else:
                print("No jobs found.")

        elif arg == "--help" or arg == "-h":
            print("""
Usage: python3 manual_job_search.py [OPTIONS]

Options:
  --parse, -p       Parse jobs from text file and export to CSV
  --browse, -b     Open browser tabs
  --paste, -p      Open text file for pasting
  --stats          Show job statistics
  --gui            Force GUI mode (default if available)
  --help, -h       Show this help

Examples:
  python3 manual_job_search.py           # Start GUI
  python3 manual_job_search.py --browse   # Open browser tabs
  python3 manual_job_search.py --parse    # Parse and export

No arguments: Opens GUI (if available) or browser tabs
""")

        else:
            print(f"Unknown option: {arg}")
            print("Use --help for usage information")

    else:
        # Default: open browser tabs
        open_browser_tabs()
        open_text_file()
        print("Instructions:")
        print("1. Browse jobs in opened tabs")
        print("2. Paste job content into text file")
        print("3. Run: python3 manual_job_search.py --parse")


if __name__ == "__main__":
    main()
