import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from fake_useragent import UserAgent
from random import uniform
import re


PROXY_API_KEY = "4576b27ec127e3bd6152ee9a40e2fdc4"  

ua = UserAgent()

def fetch_page_with_proxy(url):
    """Fetch the page using a proxy service"""
    proxy_url = f"https://api.scraperapi.com?api_key={PROXY_API_KEY}&url={url}"

    headers = {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    }

    retries = 5  
    for i in range(retries):
        try:
            response = requests.get(proxy_url, headers=headers, timeout=30)
            if response.status_code == 200:
                return response.text
            elif response.status_code == 403:
                print("Blocked! Changing proxy or User-Agent...")
                time.sleep(5)
            else:
                print(f"Unexpected error: {response.status_code}, Retrying...")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
        time.sleep(uniform(2, 5))  
    return None

def extract_job_details(job_card):
    """Extract job details from a job listing"""
    details = {
        "title": None,
        "company": None,
        "location": None,
        "salary": "Not Disclosed",
        "job_desc": None,
        "date_posted": None,
        "job_url": None
    }

    try:
     
        title_elem = job_card.find("h2", class_=re.compile("jobTitle|title", re.I))
        if title_elem:
            details["title"] = title_elem.get_text(strip=True)

        
        company_elem = job_card.find(["span", "div"], class_=re.compile("company|employer", re.I))
        if company_elem:
            details["company"] = company_elem.get_text(strip=True)

       
        location_elem = job_card.find("div", class_=re.compile("location|workplace", re.I))
        if location_elem:
            details["location"] = location_elem.get_text(strip=True)

        salary_elem = job_card.find(["div", "span"], class_=re.compile("salary|payment", re.I))
        if salary_elem:
            details["salary"] = salary_elem.get_text(strip=True)

        
        desc_elem = job_card.find("div", class_=re.compile("job-snippet|description", re.I))
        if desc_elem:
            details["job_desc"] = ' '.join(desc_elem.get_text(strip=True).split())

        
        date_elem = job_card.find(["span", "div"], class_=re.compile("date|posted-date", re.I))
        if date_elem:
            details["date_posted"] = date_elem.get_text(strip=True).replace("Posted", "").strip()

        url_elem = job_card.find("a", class_=re.compile("jobtitle|job-link", re.I))
        if url_elem and url_elem.get("href"):
            job_url = url_elem["href"]
            if not job_url.startswith("https://"):
                job_url = "https://www.indeed.com" + job_url
            details["job_url"] = job_url

            
            if not details["job_desc"]:
                details["job_desc"] = fetch_full_job_description(job_url)

    except Exception as e:
        print(f"Error extracting job details: {e}")

    return details

def fetch_full_job_description(job_url):
    """Fetch full job description from job detail page"""
    try:
        html_content = fetch_page_with_proxy(job_url)
        if html_content:
            soup = BeautifulSoup(html_content, "html.parser")
            desc_elem = soup.find("div", class_=re.compile("jobsearch-jobDescriptionText|description-container", re.I))
            if desc_elem:
                return ' '.join(desc_elem.get_text(strip=True).split())
    except Exception as e:
        print(f"Error fetching full job description: {e}")
    return None

def scrape_indeed_jobs(num_pages, job_role, job_location):
    """Scrape Indeed job listings"""
    data = {
        "job_title": [],
        "company": [],
        "location": [],
        "salary": [],
        "job_description": [],
        "date_posted": [],
        "job_url": []
    }

    base_url = f"https://www.indeed.com/jobs?q={job_role.replace(' ', '+')}&l={job_location.replace(' ', '+')}"

    for page in range(num_pages):
        print(f"Scraping page {page + 1}...")

        
        page_url = f"{base_url}&start={page * 10}"

        html_content = fetch_page_with_proxy(page_url)
        if not html_content:
            print(f"Skipping page {page + 1} due to failed request.")
            continue

        soup = BeautifulSoup(html_content, "html.parser")
        job_cards = soup.find_all("div", class_=re.compile("job_seen_beacon|jobsearch-ResultsCard|job-card", re.I))

        if not job_cards:
            print(f"No job cards found on page {page + 1}")
            continue

        for job in job_cards:
            details = extract_job_details(job)

            if details["title"]:
                data["job_title"].append(details["title"])
                data["company"].append(details["company"])
                data["location"].append(details["location"])
                data["salary"].append(details["salary"])
                data["job_description"].append(details["job_desc"])
                data["date_posted"].append(details["date_posted"])
                data["job_url"].append(details["job_url"])

       
        time.sleep(uniform(3, 7))

    return data

def main():
    """Main function to get user input and run the scraper"""
    try:
        job_role = input("Enter the job role (e.g., software developer): ")
        job_location = input("Enter the job location (e.g., Dubai): ")
        num_pages = int(input("Enter the number of pages to scrape: "))

        print("Starting job scraping...")
        job_data = scrape_indeed_jobs(num_pages, job_role, job_location)

        df = pd.DataFrame(job_data)

        df = df.dropna(subset=['job_title'])
        df = df.replace('', None)

        output_file = "indeed_job_listings.csv"
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"Data saved to '{output_file}'")

        print("\nScraping Summary:")
        print(f"Total jobs collected: {len(df)}")
        print(f"Jobs with descriptions: {df['job_description'].notna().sum()}")
        print(f"Jobs with posting dates: {df['date_posted'].notna().sum()}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
