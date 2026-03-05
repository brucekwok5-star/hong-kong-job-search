# Hong Kong Job Search Program

Python program to search job sites (JobsDB, eFinancialCareers, Indeed) for Hong Kong positions and export results to Google Sheets.

## Search Criteria

- **Location**: Hong Kong
- **Posted Within**: Last 7 days
- **Job Titles**: Team Lead OR Manager
- **Keywords**: Jenkins OR Kubernetes

## Installation

1. Install Python dependencies:

```bash
pip install -r requirements.txt
```

2. Install Chrome browser (if not already installed)

## Google Sheets Setup

To export results to Google Sheets, you need to set up Google Cloud credentials:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable **Google Sheets API** and **Google Drive API**
4. Go to **IAM & Admin** > **Service Accounts**
5. Create a service account and download the JSON credentials
6. Rename the downloaded file to `credentials.json` and place it in this directory
7. Create a new Google Sheet and share it with the service account email (found in the credentials file)

## Usage

### Basic Usage (saves to CSV if Google Sheets not configured):

```bash
python job_search.py
```

### Run in headless mode (no browser window):

```bash
python job_search.py --headless
```

### Custom keywords:

```bash
python job_search.py --keywords "Jenkins" "Kubernetes" --titles "Team Lead" "Manager"
```

## Output

- Results are displayed in the console as a table
- Results are exported to Google Sheets (if configured) or saved to `hong_kong_jobs.csv`

## Anti-Bot Protection

The program implements several techniques to bypass anti-bot protection:
- Random delays between requests (3-8 seconds)
- Realistic user agent
- Headless mode detection prevention
- Randomized window sizes

If you still encounter issues:
1. Run without `--headless` to see what's happening
2. Increase the delay times in the `CONFIG` section
3. Consider using `undetected-chromedriver` package

## Troubleshooting

### No jobs found
- The job sites may have strong anti-bot protection
- Try running in non-headless mode to see if the browser is being blocked
- Increase delays in the CONFIG section

### Google Sheets authentication fails
- Make sure credentials.json is properly configured
- Check that the service account has access to the spreadsheet
- Ensure APIs are enabled in Google Cloud Console

## Requirements

- Python 3.8+
- Chrome browser
- ChromeDriver (automatically installed by webdriver-manager)
