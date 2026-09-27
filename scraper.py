import json
import os
import sys
import requests
from datetime import datetime


def load_config(config_path="config.json"):
    if not os.path.exists(config_path):
        print(f"❌ Configuration file '{config_path}' not found. Please run setup.py first.")
        sys.exit(1)
    
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


class JobScraper:
    def __init__(self, config):
        self.roles = [r.lower() for r in config.get("target_roles", [])]
        self.locations = [l.lower() for l in config.get("target_locations", [])]
        self.max_results = config.get("max_results_per_run", 25)
        self.api_url = "https://www.arbeitnow.com/api/job-board-api"

    def fetch_jobs(self):
        print("🔍 Querying job board APIs...")
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except requests.RequestException as e:
            print(f"❌ API Request failed: {e}")
            return []

    def matches_criteria(self, job):
        title = job.get("title", "").lower()
        location = job.get("location", "").lower()
        tags = [t.lower() for t in job.get("tags", [])]
        
        # Check title or tag matches
        role_match = any(role in title or any(role in tag for tag in tags) for role in self.roles) if self.roles else True
        
        # Check location matches
        location_match = any(loc in location for loc in self.locations) if self.locations else True

        return role_match and location_match

    def run(self):
        raw_jobs = self.fetch_jobs()
        if not raw_jobs:
            print("⚠️ No job listings fetched.")
            return []

        filtered_leads = []
        for j in raw_jobs:
            if len(filtered_leads) >= self.max_results:
                break

            if self.matches_criteria(j):
                lead = {
                    "title": j.get("title"),
                    "company": j.get("company_name"),
                    "location": j.get("location"),
                    "url": j.get("url"),
                    "remote": j.get("remote", False),
                    "tags": ", ".join(j.get("tags", [])),
                    "scraped_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                }
                filtered_leads.append(lead)

        print(f"✅ Extracted {len(filtered_leads)} relevant job lead(s) matching configuration criteria.")
        return filtered_leads


if __name__ == "__main__":
    config = load_config()
    scraper = JobScraper(config)
    leads = scraper.run()
    
    if leads:
        print("\n--- SAMPLE EXTRACTED LEADS ---")
        for idx, lead in enumerate(leads[:3], 1):
            print(f"\n[{idx}] {lead['title']} at {lead['company']}")
            print(f"    Location: {lead['location']} | Remote: {lead['remote']}")
            print(f"    URL: {lead['url']}")