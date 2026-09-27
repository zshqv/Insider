import json
import requests


def load_config():
    with open("config.json", "r") as f:
        return json.load(f)


class JobScraper:
    def __init__(self, config):
        self.target_titles = [t.lower() for t in config.get("target_titles", [])]
        self.locations = [l.lower() for l in config.get("locations", [])]

    def run(self):
        print("🔍 Querying job board APIs...")
        url = "https://www.arbeitnow.com/api/job-board-api"
        leads = []

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json().get("data", [])

            for job in data:
                title = job.get("title", "")
                location = job.get("location", "")

                title_match = any(t in title.lower() for t in self.target_titles) if self.target_titles else True
                location_match = any(l in location.lower() for l in self.locations) if self.locations else True

                if title_match and location_match:
                    leads.append({
                        "title": title,
                        "company": job.get("company_name", "N/A"),
                        "location": location,
                        "url": job.get("url", ""),
                        "date": job.get("created_at", "N/A")
                    })

            print(f"✅ Extracted {len(leads)} relevant job lead(s) matching configuration criteria.")
            return leads

        except Exception as e:
            print(f"❌ Error fetching job listings: {e}")
            return []