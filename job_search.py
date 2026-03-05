#!/usr/bin/env python3
"""
Hong Kong Job Search Program
Searches JobsDB, Indeed, eFinancialCareers for Hong Kong jobs
"""

import time
import random
import csv
import os
from dataclasses import dataclass
from typing import List, Optional
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CONFIG = {
    'min_delay': 3,
    'max_delay': 6,
    'headless': False,
    'debug': True,
}


@dataclass
class Job:
    title: str
    company: str
    source: str
    skills: str
    posted_date: str
    link: str
    location: str = "Hong Kong"


class JobSearchBase:
    def __init__(self):
        self.jobs: List[Job] = []
        self.driver = None

    def random_delay(self):
        delay = random.uniform(CONFIG['min_delay'], CONFIG['max_delay'])
        logger.info(f"Waiting {delay:.2f} seconds...")
        time.sleep(delay)

    def take_screenshot(self, name: str):
        if CONFIG['debug']:
            filename = f"screenshots/{name}_{int(time.time())}.png"
            os.makedirs("screenshots", exist_ok=True)
            try:
                self.driver.save_screenshot(filename)
                logger.info(f"Screenshot saved: {filename}")
            except Exception as e:
                logger.warning(f"Could not save screenshot: {e}")

    def setup_driver(self):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service

        options = Options()

        if CONFIG['headless']:
            options.add_argument('--headless=new')

        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--start-maximized')

        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)

        prefs = {
            'profile.default_content_setting_values.notifications': 2,
            'profile.geo_enabled': False,
        }
        options.add_experimental_option('prefs', prefs)

        # Use webdriver-manager
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)

        # Anti-detection
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })

        return self.driver

    def close_driver(self):
        if self.driver:
            self.driver.quit()

    def search(self) -> List[Job]:
        raise NotImplementedError


class JobsDBSearcher(JobSearchBase):
    def __init__(self):
        super().__init__()
        self.base_url = "https://jobsdb.com/hk"

    def search(self, title_keywords: List[str] = None, job_keywords: List[str] = None) -> List[Job]:
        if title_keywords is None:
            title_keywords = ["Team Lead", "Manager"]
        if job_keywords is None:
            job_keywords = ["Jenkins", "Kubernetes"]

        logger.info("Searching JobsDB...")

        try:
            driver = self.setup_driver()
            search_query = "Jenkins Kubernetes"
            url = f"{self.base_url}/en/search/jobs?keywords={search_query.replace(' ', '%20')}&location=Hong+Kong"

            logger.info(f"Navigating to: {url}")
            driver.get(url)

            self.random_delay()
            self.take_screenshot("jobsdb_initial")

            time.sleep(5)
            job_cards = self._extract_jobs(driver)

            self.close_driver()
            return job_cards

        except Exception as e:
            logger.error(f"Error searching JobsDB: {e}")
            self.close_driver()
            return []

    def _extract_jobs(self, driver) -> List[Job]:
        jobs = []

        try:
            from selenium.webdriver.common.by import By

            selectors = [
                "article.job-card",
                "li.job-brief-searchResult",
                ".job-card",
                ".jobs-search-results-list li",
                "[data-job-id]",
            ]

            cards = []
            for selector in selectors:
                try:
                    cards = driver.find_elements(By.CSS_SELECTOR, selector)
                    if cards:
                        logger.info(f"Found {len(cards)} elements using selector: {selector}")
                        break
                except:
                    continue

            for card in cards:
                try:
                    job = self._parse_job_card(card)
                    if job:
                        jobs.append(job)
                except:
                    continue

        except Exception as e:
            logger.error(f"Error extracting jobs from JobsDB: {e}")

        logger.info(f"Extracted {len(jobs)} jobs from JobsDB")
        return jobs

    def _parse_job_card(self, card) -> Optional[Job]:
        try:
            from selenium.webdriver.common.by import By

            title, company, link, posted_date = "", "", "", ""

            try:
                link_elem = card.find_element(By.CSS_SELECTOR, "a")
                link = link_elem.get_attribute("href") or ""
            except:
                pass

            for selector in ["a", "h3", ".job-title", ".title"]:
                try:
                    title_elem = card.find_element(By.CSS_SELECTOR, selector)
                    title = title_elem.text.strip()
                    if title and len(title) > 3:
                        if not link:
                            link = title_elem.get_attribute("href") or ""
                        break
                except:
                    continue

            for selector in [".company-name", ".company", ".employer"]:
                try:
                    company_elem = card.find_element(By.CSS_SELECTOR, selector)
                    company = company_elem.text.strip()
                    if company:
                        break
                except:
                    continue

            for selector in [".posted-date", ".date", ".job-brief-posted"]:
                try:
                    date_elem = card.find_element(By.CSS_SELECTOR, selector)
                    posted_date = date_elem.text.strip()
                    break
                except:
                    pass

            if title and len(title) > 3:
                return Job(
                    title=title[:200],
                    company=company[:100] if company else "N/A",
                    source="JobsDB",
                    skills="",
                    posted_date=posted_date[:50],
                    link=link[:500] if link else "N/A"
                )

        except:
            pass

        return None


class IndeedSearcher(JobSearchBase):
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.indeed.hk"

    def search(self, title_keywords: List[str] = None, job_keywords: List[str] = None) -> List[Job]:
        if title_keywords is None:
            title_keywords = ["Team Lead", "Manager"]
        if job_keywords is None:
            job_keywords = ["Jenkins", "Kubernetes"]

        logger.info("Searching Indeed...")

        try:
            driver = self.setup_driver()
            search_query = "Jenkins Kubernetes"
            url = f"{self.base_url}/jobs?q={search_query.replace(' ', '%20')}&l=Hong+Kong"

            logger.info(f"Navigating to: {url}")
            driver.get(url)

            self.random_delay()
            self.take_screenshot("indeed_initial")

            time.sleep(5)
            job_cards = self._extract_jobs(driver)

            self.close_driver()
            return job_cards

        except Exception as e:
            logger.error(f"Error searching Indeed: {e}")
            self.close_driver()
            return []

    def _extract_jobs(self, driver) -> List[Job]:
        jobs = []

        try:
            from selenium.webdriver.common.by import By

            selectors = [
                ".job-card",
                ".jobsearch-ResultsList li",
                ".job-card-container",
                ".job-brief"
            ]

            cards = []
            for selector in selectors:
                try:
                    cards = driver.find_elements(By.CSS_SELECTOR, selector)
                    if len(cards) > 3:
                        logger.info(f"Found {len(cards)} elements using selector: {selector}")
                        break
                except:
                    continue

            for card in cards[:30]:
                try:
                    job = self._parse_job_card(card)
                    if job:
                        jobs.append(job)
                except:
                    continue

        except Exception as e:
            logger.error(f"Error extracting jobs from Indeed: {e}")

        logger.info(f"Extracted {len(jobs)} jobs from Indeed")
        return jobs

    def _parse_job_card(self, card) -> Optional[Job]:
        try:
            from selenium.webdriver.common.by import By

            title, company, link, posted_date = "", "", "", ""

            for selector in ["h2.jobTitle", ".job-title", "a.jobtitle"]:
                try:
                    title_elem = card.find_element(By.CSS_SELECTOR, selector)
                    title = title_elem.text.strip()
                    if title:
                        try:
                            link = title_elem.get_attribute("href")
                        except:
                            pass
                        break
                except:
                    continue

            for selector in [".companyName", ".company", ".employer"]:
                try:
                    company_elem = card.find_element(By.CSS_SELECTOR, selector)
                    company = company_elem.text.strip()
                    if company:
                        break
                except:
                    continue

            for selector in [".date", ".job-age", ".post-date"]:
                try:
                    date_elem = card.find_element(By.CSS_SELECTOR, selector)
                    posted_date = date_elem.text.strip()
                    break
                except:
                    continue

            if title and len(title) > 3:
                return Job(
                    title=title[:200],
                    company=company[:100] if company else "N/A",
                    source="Indeed",
                    skills="",
                    posted_date=posted_date[:50],
                    link=link[:500] if link else "N/A"
                )

        except:
            pass

        return None


class EFinancialCareersSearcher(JobSearchBase):
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.efinancialcareers.hk"

    def search(self, title_keywords: List[str] = None, job_keywords: List[str] = None) -> List[Job]:
        if title_keywords is None:
            title_keywords = ["Team Lead", "Manager"]
        if job_keywords is None:
            job_keywords = ["Jenkins", "Kubernetes"]

        logger.info("Searching eFinancialCareers...")

        try:
            driver = self.setup_driver()
            search_query = "Jenkins Kubernetes"
            url = f"{self.base_url}/jobs?query={search_query.replace(' ', '+')}&location=Hong+Kong"

            logger.info(f"Navigating to: {url}")
            driver.get(url)

            self.random_delay()
            self.take_screenshot("efinancial_initial")

            time.sleep(5)
            job_cards = self._extract_jobs(driver)

            self.close_driver()
            return job_cards

        except Exception as e:
            logger.error(f"Error searching eFinancialCareers: {e}")
            self.close_driver()
            return []

    def _extract_jobs(self, driver) -> List[Job]:
        jobs = []

        try:
            from selenium.webdriver.common.by import By

            selectors = [
                ".job-listing",
                ".job-item",
                "article.job",
                ".search-result",
            ]

            cards = []
            for selector in selectors:
                try:
                    cards = driver.find_elements(By.CSS_SELECTOR, selector)
                    if cards:
                        logger.info(f"Found {len(cards)} cards using selector: {selector}")
                        break
                except:
                    continue

            for card in cards:
                try:
                    job = self._parse_job_card(card)
                    if job:
                        jobs.append(job)
                except:
                    continue

        except Exception as e:
            logger.error(f"Error extracting jobs from eFinancialCareers: {e}")

        logger.info(f"Extracted {len(jobs)} jobs from eFinancialCareers")
        return jobs

    def _parse_job_card(self, card) -> Optional[Job]:
        try:
            from selenium.webdriver.common.by import By

            title, company, link, posted_date = "", "", "", ""

            try:
                title_elem = card.find_element(By.CSS_SELECTOR, "h3, .job-title, .title, a")
                title = title_elem.text.strip()
                if title:
                    link = title_elem.get_attribute("href") or ""
            except:
                pass

            try:
                company_elem = card.find_element(By.CSS_SELECTOR, ".company, .employer-name, .company-name")
                company = company_elem.text.strip()
            except:
                pass

            try:
                date_elem = card.find_element(By.CSS_SELECTOR, ".date, .posted-date, .job-date")
                posted_date = date_elem.text.strip()
            except:
                pass

            if title and len(title) > 3:
                return Job(
                    title=title[:200],
                    company=company[:100] if company else "N/A",
                    source="eFinancialCareers",
                    skills="",
                    posted_date=posted_date[:50],
                    link=link[:500] if link else "N/A"
                )

        except:
            pass

        return None


def save_to_csv(jobs: List[Job], filename: str = "hong_kong_jobs.csv"):
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Job Title", "Company", "Source", "Key Skills", "Posted Date", "Link", "Location"])

            for job in jobs:
                writer.writerow([
                    job.title, job.company, job.source, job.skills,
                    job.posted_date, job.link, job.location
                ])

        logger.info(f"Saved {len(jobs)} jobs to {filename}")
        return filename

    except Exception as e:
        logger.error(f"Error saving to CSV: {e}")
        return None


def run_job_search():
    logger.info("=" * 50)
    logger.info("Starting Hong Kong Job Search")
    logger.info("=" * 50)

    all_jobs = []

    searchers = [
        JobsDBSearcher(),
        IndeedSearcher(),
        EFinancialCareersSearcher()
    ]

    for searcher in searchers:
        try:
            jobs = searcher.search()
            all_jobs.extend(jobs)
            time.sleep(random.uniform(3, 6))
        except Exception as e:
            logger.error(f"Error with {searcher.__class__.__name__}: {e}")
            continue

    logger.info(f"Total jobs found: {len(all_jobs)}")

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
        logger.info("The job sites are protected by Cloudflare anti-bot.")
        logger.info("Check screenshots/ folder to see what's being blocked.")
        logger.info("\nOptions:")
        logger.info("1. Try a different network (mobile hotspot)")
        logger.info("2. Use manual browser + copy to CSV")
        logger.info("3. Use a VPN with residential IPs")

    return all_jobs


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Hong Kong Job Search Program")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--output", type=str, default="hong_kong_jobs.csv", help="Output CSV filename")

    args = parser.parse_args()

    if args.headless:
        CONFIG['headless'] = True

    run_job_search()


if __name__ == "__main__":
    main()
