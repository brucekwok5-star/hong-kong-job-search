#!/usr/bin/env python3
"""
Hong Kong Job Search Program - Alternative version using requests
This version uses HTTP requests instead of Selenium to avoid anti-bot detection
"""

import time
import csv
import random
import os
import json
import requests
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional
from bs4 import BeautifulSoup
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
CONFIG = {
    'min_delay': 3,
    'max_delay': 6,
}


@dataclass
class Job:
    """Data class to store job information"""
    title: str
    company: str
    source: str
    skills: str
    posted_date: str
    link: str
    location: str = "Hong Kong"


class RequestsJobSearcher:
    """Base class for job search using requests"""

    def __init__(self):
        self.session = requests.Session()
        self.jobs: List[Job] = []

        # Setup headers to look more like a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })

    def random_delay(self):
        """Apply random delay"""
        delay = random.uniform(CONFIG['min_delay'], CONFIG['max_delay'])
        logger.info(f"Waiting {delay:.2f} seconds...")
        time.sleep(delay)

    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch a page using requests"""
        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=30)
            logger.info(f"Response status: {response.status_code}")
            return response.text
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None


class JobsDBSearcher(RequestsJobSearcher):
    """Searcher for jobsdb.com"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://jobsdb.com/hk"

    def search(self, title_keywords: List[str] = None, job_keywords: List[str] = None) -> List[Job]:
        """Search jobsdb.com"""
        if title_keywords is None:
            title_keywords = ["Team Lead", "Manager"]
        if job_keywords is None:
            job_keywords = ["Jenkins", "Kubernetes"]

        logger.info("Searching JobsDB...")

        try:
            search_query = "Jenkins Kubernetes"
            url = f"{self.base_url}/en/search/jobs?keywords={search_query.replace(' ', '%20')}&location=Hong+Kong"

            html = self.fetch_page(url)
            if html:
                return self._extract_jobs(html)
        except Exception as e:
            logger.error(f"Error searching JobsDB: {e}")

        return []

    def _extract_jobs(self, html: str) -> List[Job]:
        """Extract job information from HTML"""
        jobs = []

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # JobsDB job card selectors
            selectors = [
                'article.job-card',
                'li.job-brief-searchResult',
                '.job-card',
                '[data-job-id]'
            ]

            for selector in selectors:
                cards = soup.select(selector)
                if cards:
                    logger.info(f"Found {len(cards)} cards with selector: {selector}")
                    for card in cards:
                        job = self._parse_job_card(card)
                        if job:
                            jobs.append(job)
                    break

        except Exception as e:
            logger.error(f"Error extracting jobs from JobsDB: {e}")

        logger.info(f"Extracted {len(jobs)} jobs from JobsDB")
        return jobs

    def _parse_job_card(self, card) -> Optional[Job]:
        """Parse individual job card"""
        try:
            # Try to find title
            title_elem = card.find(['a', 'h3', 'div'], class_=['job-title', 'title'])
            title = title_elem.text.strip() if title_elem else ""

            # Try to find company
            company_elem = card.find(['span', 'div'], class_=['company-name', 'company'])
            company = company_elem.text.strip() if company_elem else "N/A"

            # Try to find link
            link = ""
            link_elem = card.find('a')
            if link_elem:
                link = link_elem.get('href', '')
                if link and not link.startswith('http'):
                    link = f"https://jobsdb.com{link}"

            # Try to find date
            date_elem = card.find(['span', 'div'], class_=['posted-date', 'date'])
            posted_date = date_elem.text.strip() if date_elem else ""

            if title and len(title) > 3:
                return Job(
                    title=title[:200],
                    company=company[:100],
                    source="JobsDB",
                    skills="",
                    posted_date=posted_date[:50],
                    link=link[:500]
                )
        except Exception as e:
            logger.warning(f"Error parsing card: {e}")

        return None


class IndeedSearcher(RequestsJobSearcher):
    """Searcher for indeed.hk"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.indeed.hk"

    def search(self, title_keywords: List[str] = None, job_keywords: List[str] = None) -> List[Job]:
        """Search indeed.hk"""
        if title_keywords is None:
            title_keywords = ["Team Lead", "Manager"]
        if job_keywords is None:
            job_keywords = ["Jenkins", "Kubernetes"]

        logger.info("Searching Indeed...")

        try:
            search_query = "Jenkins Kubernetes"
            url = f"{self.base_url}/jobs?q={search_query.replace(' ', '%20')}&l=Hong+Kong"

            html = self.fetch_page(url)
            if html:
                return self._extract_jobs(html)
        except Exception as e:
            logger.error(f"Error searching Indeed: {e}")

        return []

    def _extract_jobs(self, html: str) -> List[Job]:
        """Extract job information from Indeed HTML"""
        jobs = []

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Indeed selectors
            cards = soup.select('.job-card, .jobsearch-ResultsList li, .job-card-container')
            logger.info(f"Found {len(cards)} cards")

            for card in cards[:30]:
                job = self._parse_job_card(card)
                if job:
                    jobs.append(job)

        except Exception as e:
            logger.error(f"Error extracting jobs from Indeed: {e}")

        logger.info(f"Extracted {len(jobs)} jobs from Indeed")
        return jobs

    def _parse_job_card(self, card) -> Optional[Job]:
        """Parse Indeed job card"""
        try:
            title_elem = card.find(['h2', 'a'], class_=['jobTitle', 'job-title', 'jobtitle'])
            title = title_elem.text.strip() if title_elem else ""

            company_elem = card.find(['span', 'div'], class_=['companyName', 'company'])
            company = company_elem.text.strip() if company_elem else "N/A"

            link = ""
            link_elem = card.find('a')
            if link_elem:
                link = link_elem.get('href', '')
                if link and not link.startswith('http'):
                    link = f"https://www.indeed.hk{link}"

            date_elem = card.find(['span', 'div'], class_=['date', 'job-age'])
            posted_date = date_elem.text.strip() if date_elem else ""

            if title and len(title) > 3:
                return Job(
                    title=title[:200],
                    company=company[:100],
                    source="Indeed",
                    skills="",
                    posted_date=posted_date[:50],
                    link=link[:500]
                )
        except Exception as e:
            logger.warning(f"Error parsing card: {e}")

        return None


class EFinancialCareersSearcher(RequestsJobSearcher):
    """Searcher for efinancialcareers.hk"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.efinancialcareers.hk"

    def search(self, title_keywords: List[str] = None, job_keywords: List[str] = None) -> List[Job]:
        """Search efinancialcareers.hk"""
        if title_keywords is None:
            title_keywords = ["Team Lead", "Manager"]
        if job_keywords is None:
            job_keywords = ["Jenkins", "Kubernetes"]

        logger.info("Searching eFinancialCareers...")

        try:
            search_query = "Jenkins Kubernetes"
            url = f"{self.base_url}/jobs?query={search_query.replace(' ', '+')}&location=Hong+Kong"

            html = self.fetch_page(url)
            if html:
                return self._extract_jobs(html)
        except Exception as e:
            logger.error(f"Error searching eFinancialCareers: {e}")

        return []

    def _extract_jobs(self, html: str) -> List[Job]:
        """Extract job information from eFinancialCareers HTML"""
        jobs = []

        try:
            soup = BeautifulSoup(html, 'html.parser')

            cards = soup.select('.job-listing, .job-item, article.job, .search-result')
            logger.info(f"Found {len(cards)} cards")

            for card in cards:
                job = self._parse_job_card(card)
                if job:
                    jobs.append(job)

        except Exception as e:
            logger.error(f"Error extracting jobs from eFinancialCareers: {e}")

        logger.info(f"Extracted {len(jobs)} jobs from eFinancialCareers")
        return jobs

    def _parse_job_card(self, card) -> Optional[Job]:
        """Parse eFinancialCareers job card"""
        try:
            title_elem = card.find(['h3', 'a'], class_=['job-title', 'title'])
            title = title_elem.text.strip() if title_elem else ""

            company_elem = card.find(['span', 'div'], class_=['company', 'employer-name'])
            company = company_elem.text.strip() if company_elem else "N/A"

            link = ""
            link_elem = card.find('a')
            if link_elem:
                link = link_elem.get('href', '')
                if link and not link.startswith('http'):
                    link = f"https://www.efinancialcareers.hk{link}"

            date_elem = card.find(['span', 'div'], class_=['date', 'posted-date'])
            posted_date = date_elem.text.strip() if date_elem else ""

            if title and len(title) > 3:
                return Job(
                    title=title[:200],
                    company=company[:100],
                    source="eFinancialCareers",
                    skills="",
                    posted_date=posted_date[:50],
                    link=link[:500]
                )
        except Exception as e:
            logger.warning(f"Error parsing card: {e}")

        return None


def save_to_csv(jobs: List[Job], filename: str = "hong_kong_jobs.csv"):
    """Save jobs to CSV file"""
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Job Title", "Company", "Source", "Key Skills", "Posted Date", "Link", "Location"])

            for job in jobs:
                writer.writerow([
                    job.title,
                    job.company,
                    job.source,
                    job.skills,
                    job.posted_date,
                    job.link,
                    job.location
                ])

        logger.info(f"Saved {len(jobs)} jobs to {filename}")
        return filename

    except Exception as e:
        logger.error(f"Error saving to CSV: {e}")
        return None


def run_job_search():
    """Main function to run the job search"""
    logger.info("=" * 50)
    logger.info("Starting Hong Kong Job Search (Requests Version)")
    logger.info("=" * 50)

    all_jobs = []

    # Initialize searchers
    searchers = [
        JobsDBSearcher(),
        IndeedSearcher(),
        EFinancialCareersSearcher()
    ]

    # Run searches
    for searcher in searchers:
        try:
            jobs = searcher.search()
            all_jobs.extend(jobs)
            time.sleep(random.uniform(3, 6))
        except Exception as e:
            logger.error(f"Error with {searcher.__class__.__name__}: {e}")
            continue

    logger.info(f"Total jobs found: {len(all_jobs)}")

    # Display results
    if all_jobs:
        print("\n" + "=" * 80)
        print("JOB SEARCH RESULTS")
        print("=" * 80)
        print(f"{'#':<3} {'Job Title':<40} {'Company':<20} {'Source':<15}")
        print("-" * 80)
        for i, job in enumerate(all_jobs, 1):
            title = job.title[:37] + "..." if len(job.title) > 40 else job.title
            company = job.company[:17] + "..." if len(job.company) > 20 else job.company
            print(f"{i:<3} {title:<40} {company:<20} {job.source:<15}")
        print("=" * 80)

        csv_file = save_to_csv(all_jobs)
        if csv_file:
            print(f"\nResults saved to: {csv_file}")
    else:
        logger.info("No jobs found.")
        logger.info("\nAll three job sites (JobsDB, Indeed, eFinancialCareers) use Cloudflare")
        logger.info("anti-bot protection which blocks automated requests.")
        logger.info("\nPossible solutions:")
        logger.info("1. Use a browser extension to manually export job data")
        logger.info("2. Use a proxy service with residential IPs")
        logger.info("3. Run this script in a different environment with better network")
        logger.info("4. Use undetected-chromedriver in a properly configured environment")

    return all_jobs


def main():
    """Entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Hong Kong Job Search Program")
    parser.add_argument("--keywords", type=str, nargs="+",
                        default=["Jenkins", "Kubernetes"],
                        help="Job keywords to search for")
    parser.add_argument("--titles", type=str, nargs="+",
                        default=["Team Lead", "Manager"],
                        help="Job titles to search for")
    parser.add_argument("--output", type=str, default="hong_kong_jobs.csv",
                        help="Output CSV filename")

    args = parser.parse_args()

    run_job_search()


if __name__ == "__main__":
    main()
