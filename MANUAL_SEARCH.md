# Hong Kong Job Search - Search URLs

Due to strong anti-bot protection on job sites, please manually browse these URLs and copy job data to hong_kong_jobs.csv

## Search URLs

### JobsDB
https://jobsdb.com/hk/en/search/jobs?keywords=Jenkins%20Kubernetes&location=Hong+Kong

### Indeed
https://www.indeed.hk/jobs?q=Jenkins%20Kubernetes&l=Hong+Kong

### eFinancialCareers
https://www.efinancialcareers.hk/jobs?query=Jenkins+Kubernetes&location=Hong+Kong

## Instructions

1. Open the above URLs in your browser (Chrome recommended)
2. Manually browse and find jobs matching:
   - Location: Hong Kong
   - Posted: Last 7 days
   - Title: "Team Lead" OR "Manager"
   - Keywords: "Jenkins" OR "Kubernetes"
3. For each job, copy the following to hong_kong_jobs.csv:
   - Job Title
   - Company Name
   - Source (JobsDB / Indeed / eFinancialCareers)
   - Key Skills (comma separated)
   - Posted Date
   - Link to job posting
   - Location (Hong Kong)

## CSV Format

Job Title,Company,Source,Key Skills,Posted Date,Link,Location
Senior DevOps Engineer,ABC Company,JobsDB,"Jenkins, Kubernetes",2 days ago,https://...,Hong Kong

## Alternative Solutions

If you need automated scraping:

1. **Use a different network** - Some networks have better access to these sites
2. **Use residential proxies** - Services like Bright Data provide residential IPs
3. **Use browser automation tools** - Tools like Browse.ai or Oxylabs can extract data
4. **Use official APIs** - Some job sites offer official APIs for job listings

## Notes

The anti-bot protection (Cloudflare) on these sites specifically blocks:
- Selenium/WebDriver automation
- Headless browsers
- Automated requests without proper browser fingerprints
