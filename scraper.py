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

        # Seniority exclusions
        self.seniority_exclusions = [
            "senior", "sr.", "sr ", "lead", "principal", "head of", "director", "manager", "vp", "vice president"
        ]

        # Non-finance tech exclusions
        self.tech_exclusions = [
            "full stack", "frontend", "backend", "devops", "software engineer",
            "react", "node", "java", "salesforce", "recruiter", "marketing",
            "customer support", "driver", "nursing", "fitness"
        ]

        # Market & Trading exclusions
        self.market_exclusions = [
            "trader", "trading", "market maker", "execution", "derivatives", 
            "fixed income", "equity sales", "commodities", "fx trader", "algo trading"
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

    def _determine_workplace_type(self, title, location, job_data=None):
        combined = f"{title} {location}".lower()
        if "hybrid" in combined:
            return "Hybrid 🏢🏠"
        elif "remote" in combined or (job_data and job_data.get("remote")):
            return "Remote 🌐"
        return "On-site 🏢"

    def _is_valid_lead(self, title, location):
        title_lower = title.lower()
        location_lower = location.lower()

        if any(sen in title_lower for sen in self.seniority_exclusions):
            return False
        if any(tech in title_lower for tech in self.tech_exclusions):
            return False
        if any(mkt in title_lower for mkt in self.market_exclusions):
            return False

        title_match = any(target in title_lower for target in self.target_titles) if self.target_titles else True
        location_match = any(loc in location_lower for loc in self.locations) if self.locations else True

        return title_match and location_match

    def fetch_arbeitnow(self):
        url = "https://www.arbeitnow.com/api/job-board-api"
        leads = []
        try:
            res = requests.get(url, timeout=10)
            res.raise_for_status()
            for job in res.json().get("data", []):
                title = job.get("title", "")
                loc = job.get("location", "")
                if self._is_valid_lead(title, loc):
                    leads.append({
                        "title": title,
                        "company": job.get("company_name", "N/A"),
                        "location": loc,
                        "workplace_type": self._determine_workplace_type(title, loc, job),
                        "url": job.get("url", ""),
                        "date": self._format_date(job.get("created_at")),
                        "source": "Arbeitnow"
                    })
        except Exception as e:
            print(f"⚠️ Arbeitnow API fetch failed: {e}")
        return leads

    def fetch_remotive(self):
        url = "https://remotive.com/api/remote-jobs?category=finance-legal"
        leads = []
        try:
            res = requests.get(url, timeout=10)
            res.raise_for_status()
            for job in res.json().get("jobs", []):
                title = job.get("title", "")
                loc = job.get("candidate_required_location", "Remote")
                if self._is_valid_lead(title, loc):
                    leads.append({
                        "title": title,
                        "company": job.get("company_name", "N/A"),
                        "location": loc or "Remote",
                        "workplace_type": "Remote 🌐",
                        "url": job.get("url", ""),
                        "date": self._format_date(job.get("publication_date")),
                        "source": "Remotive"
                    })
        except Exception as e:
            print(f"⚠️ Remotive API fetch failed: {e}")
        return leads

    def fetch_jobicy(self):
        url = "https://jobicy.com/api/v2/remote-jobs?industry=finance"
        leads = []
        try:
            res = requests.get(url, timeout=10)
            res.raise_for_status()
            for job in res.json().get("jobs", []):
                title = job.get("jobTitle", "")
                loc = job.get("jobGeo", "Remote")
                if self._is_valid_lead(title, loc):
                    leads.append({
                        "title": title,
                        "company": job.get("companyName", "N/A"),
                        "location": loc or "Remote",
                        "workplace_type": self._determine_workplace_type(title, loc),
                        "url": job.get("url", ""),
                        "date": self._format_date(job.get("pubDate")),
                        "source": "Jobicy"
                    })
        except Exception as e:
            print(f"⚠️ Jobicy API fetch failed: {e}")
        return leads

    def run(self):
        print("🔍 Querying multi-source pipeline (Arbeitnow, Remotive, Jobicy)...")
        all_leads = []
        all_leads.extend(self.fetch_arbeitnow())
        all_leads.extend(self.fetch_remotive())
        all_leads.extend(self.fetch_jobicy())

        unique_leads = {}
        for lead in all_leads:
            unique_key = f"{lead['title'].lower()}-{lead['company'].lower()}"
            if unique_key not in unique_leads:
                unique_leads[unique_key] = lead

        final_leads = list(unique_leads.values())
        print(f"✅ Extracted {len(final_leads)} deduplicated finance lead(s).")
        return final_leads