import json
from datetime import datetime
import requests


def load_config():
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except Exception:
        return {}


class JobScraper:
    def __init__(self, config=None):
        if config is None:
            config = load_config()
        self.target_titles = [t.lower() for t in config.get("target_roles", [])]
        self.locations = [l.lower() for l in config.get("target_locations", [])]

        # Explicit negative keywords to drop generic tech/engineering listings
        self.exclude_keywords = [
            "full stack", "frontend", "backend", "devops", "software engineer",
            "react", "node", "java", "salesforce", "recruiter", "marketing",
            "customer support", "driver", "nursing", "fitness"
        ]

    def _format_date(self, raw_date):
        if not raw_date:
            return datetime.now().strftime("%Y-%m-%d")
        if isinstance(raw_date, (int, float)):
            return datetime.fromtimestamp(raw_date).strftime("%Y-%m-%d")
        try:
            return datetime.fromtimestamp(int(raw_date)).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            return str(raw_date)[:10]

    def run(self):
        print("🔍 Querying job board APIs for Finance & Quantitative positions...")
        url = "https://www.arbeitnow.com/api/job-board-api"
        leads = []

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json().get("data", [])

            for job in data:
                title = job.get("title", "").lower()
                location = job.get("location", "").lower()

                # 1. Skip if title contains explicit negative keywords
                if any(neg in title for neg in self.exclude_keywords):
                    continue

                # 2. Strict keyword match for target finance titles
                title_match = any(target in title for target in self.target_titles) if self.target_titles else True

                # 3. Location match
                location_match = any(loc in location for loc in self.locations) if self.locations else True

                if title_match and location_match:
                    leads.append({
                        "title": job.get("title", ""),
                        "company": job.get("company_name", "N/A"),
                        "location": job.get("location", "N/A"),
                        "url": job.get("url", ""),
                        "date": self._format_date(job.get("created_at"))
                    })

            print(f"✅ Extracted {len(leads)} high-intent finance lead(s) matching criteria.")
            return leads

        except Exception as e:
            print(f"❌ Error fetching job listings: {e}")
            return []