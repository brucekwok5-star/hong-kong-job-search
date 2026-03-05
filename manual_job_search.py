#!/usr/bin/env python3
"""
Manual Job Search Helper
1. Open 3 browser tabs with job search URLs
2. Open text file for pasting raw job content
3. Auto-parse and export to CSV
"""

import os
import subprocess
import sys
import re
from datetime import datetime

# Search URLs
SEARCH_URLS = [
    ("Indeed", "https://hk.indeed.com/jobs?q=(jenkins+AND+devops)+AND+(lead+or+manager)&l=Hong+Kong&fromage=7"),
    ("eFinancialCareers", "https://www.efinancialcareers.hk/jobs/(jenkins-and-devops)-and-(lead-or-manager-or-senior)/in-hong-kong"),
    ("JobsDB", "https://hk.jobsdb.com/(jenkins-AND-devops)-AND-(lead-AND-senior-AND-manager)-jobs/in-Hong-Kong-SAR?daterange=7")
]

# Common skills to look for
SKILLS_LIST = [
    "Kubernetes", "K8S", "Jenkins", "Docker", "Terraform", "Ansible",
    "AWS", "Azure", "GCP", "Google Cloud", "Python", "Java", "NodeJS",
    "Git", "GitLab", "GitHub", "Bitbucket", "SonarQube", "Chef", "Puppet",
    "ArgoCD", "Linux", "Unix", "DevOps", "DevSecOps", "CI/CD", "Pipeline",
    "Cloud", "Azure", "Splunk", "MongoDB", "Oracle", "NoSQL", "Redis"
]


def open_browser_tabs():
    """Open 3 browser tabs with search URLs"""
    print("Opening browser tabs...")
    for name, url in SEARCH_URLS:
        subprocess.run(["open", url])
        print(f"  - {name}")
    print()


def open_text_file():
    """Open text file with timestamp for user to paste job details"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"job_details_{timestamp}.txt"
    filepath = os.path.abspath(filename)

    template = f"""# PASTE RAW JOB CONTENT HERE
# - Copy job details from browser
# - Paste multiple jobs (program will auto-parse each job)
# - Save file, then run: python3 manual_job_search.py --parse

---

PASTE BELOW THIS LINE:

"""
    with open(filepath, 'w') as f:
        f.write(template)

    subprocess.run(["open", "-a", "TextEdit", filepath])
    return filepath


def extract_jobs_from_raw(content, source_hint=""):
    """Auto-parse raw job content into structured jobs"""
    jobs = []

    # Split by common job separators
    # Look for patterns like "Job title:" or multiple newlines
    sections = re.split(r'\n{3,}', content)

    current_job = {
        'title': '',
        'company': '',
        'source': source_hint,
        'skills': [],
        'posted_date': '',
        'link': '',
        'location': 'Hong Kong'
    }

    full_text = content

    # Try to detect source
    if 'indeed' in full_text.lower():
        current_job['source'] = 'Indeed'
    elif 'efinancialcareers' in full_text.lower():
        current_job['source'] = 'eFinancialCareers'
    elif 'jobsdb' in full_text.lower():
        current_job['source'] = 'JobsDB'

    # Extract job title - usually first line or after "Job title:"
    title_match = re.search(r'(?:Job title:)?\s*([A-Z][^\n]{10,80})', full_text)
    if title_match:
        current_job['title'] = title_match.group(1).strip()

    # Extract company - look for common patterns
    company_match = re.search(r'(?:Company|Client|Employer|Pte\.? Ltd\.?|Limited|HK|International):?\s*([^\n]{3,50})', full_text, re.IGNORECASE)
    if not company_match:
        # Try Indeed pattern
        company_match = re.search(r'([A-Z][^\n]{3,40} (?:Limited|Pte\.? Ltd\.?|Ltd\.?|HK|International|Group|Corporation|Inc\.?))', full_text)
    if company_match:
        current_job['company'] = company_match.group(1).strip()

    # Extract posted date
    date_match = re.search(r'Posted\s*(\d+[hdwmy]\s*ago|Today|Yesterday)', full_text, re.IGNORECASE)
    if date_match:
        current_job['posted_date'] = date_match.group(1).strip()

    # Extract skills from content
    found_skills = []
    for skill in SKILLS_LIST:
        if re.search(r'\b' + re.escape(skill) + r'\b', full_text, re.IGNORECASE):
            found_skills.append(skill)
    current_job['skills'] = list(set(found_skills))

    # Extract link
    link_match = re.search(r'(https?://[^\s<>"]+)', full_text)
    if link_match:
        current_job['link'] = link_match.group(1).strip()

    # Only add if we have a title
    if current_job['title']:
        jobs.append(current_job)

    return jobs


def parse_and_export(filepath):
    """Parse the text file and export to CSV"""
    print("\n" + "="*70)
    print("PARSING JOB DETAILS...")
    print("="*70 + "\n")

    with open(filepath, 'r') as f:
        content = f.read()

    # Remove comments and find paste section
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
        return []

    # Auto-parse jobs
    jobs = extract_jobs_from_raw(raw_text)

    # Display results table
    if jobs:
        print(f"Found {len(jobs)} jobs:\n")
        print("-"*70)
        print(f"{'#':<3} {'Job Title':<35} {'Company':<20} {'Source':<12}")
        print("-"*70)

        for i, job in enumerate(jobs, 1):
            title = job['title'][:32] + '...' if len(job['title']) > 35 else job['title']
            company = job['company'][:17] + '...' if len(job['company']) > 20 else job['company']
            source = job['source']
            print(f"{i:<3} {title:<35} {company:<20} {source:<12}")

            # Show skills
            if job['skills']:
                print(f"    Skills: {', '.join(job['skills'][:8])}")
            if job['posted_date']:
                print(f"    Posted: {job['posted_date']}")

        print("-"*70)

        # Save to CSV
        csv_file = "hong_kong_jobs.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            f.write("Job Title,Company,Source,Key Skills,Posted Date,Link,Location\n")
            for job in jobs:
                skills = ', '.join(job['skills']) if job['skills'] else ''
                f.write(f"\"{job['title']}\",\"{job['company']}\",\"{job['source']}\",\"{skills}\",\"{job['posted_date']}\",\"{job['link']}\",\"Hong Kong\"\n")

        print(f"\nSaved to: {csv_file}\n")

    else:
        print("Could not parse jobs. Please paste in simple format:")
        print("Job Title | Company | Source | Skills | Posted Date | Link")

    return jobs


def main():
    print("="*70)
    print("  MANUAL JOB SEARCH HELPER")
    print("="*70 + "\n")

    if len(sys.argv) > 1 and sys.argv[1] == "--parse":
        # Parse existing file - find latest by modification time
        import glob
        files = glob.glob("job_details_*.txt")
        if files:
            files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            latest_file = files[0]
            print(f"Using latest file: {latest_file}\n")
            parse_and_export(latest_file)
        else:
            print("No job details file found. Run without --parse first.")
        return

    # Step 1: Open browser tabs
    print("STEP 1: Opening job search tabs...")
    open_browser_tabs()

    # Step 2: Open text file
    print("STEP 2: Opening text file for pasting...")
    filepath = open_text_file()

    # Step 3: Instructions
    print("="*70)
    print("STEP 3: PASTE JOB CONTENT")
    print("="*70)
    print(f"""
INSTRUCTIONS:
1. Browse jobs in the 3 opened tabs
2. For each job: copy the content (title, company, description)
3. Paste into the text file
4. Save the text file
5. Run: python3 manual_job_search.py --parse

The program will auto-extract:
- Job Title
- Company Name
- Skills (Kubernetes, Jenkins, AWS, etc.)
- Posted Date
- Link
""")


if __name__ == "__main__":
    main()
