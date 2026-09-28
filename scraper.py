import re
import json
import requests
from datetime import datetime

class JobScraperEngine:
    def __init__(self, config_path="config.json"):
        with open(config_path, "r") as f:
            self.config = json.load(f)
        
        self.roles = [r.lower() for r in self.config.get("target_roles", [])]
        self.priority_locs = [l.lower() for l in self.config.get("priority_locations", ["mumbai", "remote"])]
        self.secondary_locs = [l.lower() for l in self.config.get("secondary_locations", ["india", "worldwide", "remote"])]

    def is_target_role(self, title, description=""):
        text = f"{title} {description}".lower()
        
        # 1. Strict Seniority Exclusions
        senior_patterns = [
            r"\bmanager\b", r"\bhead\b", r"\bdirector\b", r"\blead\b", 
            r"\bprincipal\b", r"\bvp\b", r"\bvice president\b", r"\bchief\b", 
            r"\bsenior\b", r"\bsr\b", r"\bexec\b", r"\bexecutive\b", r"\bhead of\b"
        ]
        for pattern in senior_patterns:
            if re.search(pattern, title.lower()):
                return False

        # 2. Year of Experience (YOE) Filtering (Reject 3+ YOE requirements)
        high_yoe_pattern = r"\b([3-9]|\d{2,})\+?\s*(years?|yrs?|yoe)\b"
        if re.search(high_yoe_pattern, text):
            return False

        # 3. Explicit Match for Entry Level & Target Roles
        return any(role in title.lower() for role in self.roles)

    def is_priority_location(self, location_str):
        loc_lower = location_str.lower()
        
        # Exclude region-locked non-India locations even if "remote" is present
        excluded_regions = ["uk", "united kingdom", "us", "usa", "canada", "emea", "apac", "latam", "europe", "germany"]
        for region in excluded_regions:
            if re.search(r'\b' + region + r'\b', loc_lower):
                return False

        return any(p_loc in loc_lower for p_loc in self.priority_locs)

    def is_secondary_location(self, location_str):
        loc_lower = location_str.lower()
        return any(s_loc in loc_lower for s_loc in self.secondary_locs)

    def detect_workplace_type(self, title, location, description=""):
        combined = f"{title} {location} {description}".lower()
        if "remote" in combined:
            return "Remote 🌐"
        elif "hybrid" in combined:
            return "Hybrid 🏢"
        return "On-site 🏢"

    def fetch_arbeitnow(self):
        jobs = []
        try:
            res = requests.get("https://www.arbeitnow.com/api/job-board-api", timeout=10)
            if res.status_code == 200:
                for item in res.json().get("data", []):
                    title = item.get("title", "")
                    location = item.get("location", "")
                    description = item.get("description", "")
                    
                    if self.is_target_role(title, description):
                        is_prio = self.is_priority_location(location) or item.get("remote", False)
                        is_sec = self.is_secondary_location(location)
                        
                        if is_prio or is_sec:
                            jobs.append({
                                "title": title,
                                "company": item.get("company_name", "Unknown"),
                                "location": location,
                                "url": item.get("url"),
                                "source": "Arbeitnow",
                                "workplace_type": "Remote 🌐" if item.get("remote") else "On-site 🏢",
                                "is_priority": is_prio,
                                "date": datetime.now().strftime("%Y-%m-%d")
                            })
        except Exception as e:
            print(f"[!] Arbeitnow fetch failed: {e}")
        return jobs

    def fetch_remotive(self):
        jobs = []
        try:
            res = requests.get("https://remotive.com/api/remote-jobs?category=finance-legal", timeout=10)
            if res.status_code == 200:
                for item in res.json().get("jobs", []):
                    title = item.get("title", "")
                    location = item.get("candidate_required_location", "Worldwide")
                    description = item.get("description", "")
                    
                    if self.is_target_role(title, description):
                        is_prio = self.is_priority_location(location)
                        jobs.append({
                            "title": title,
                            "company": item.get("company_name", "Unknown"),
                            "location": location,
                            "url": item.get("url"),
                            "source": "Remotive",
                            "workplace_type": "Remote 🌐",
                            "is_priority": is_prio,
                            "date": datetime.now().strftime("%Y-%m-%d")
                        })
        except Exception as e:
            print(f"[!] Remotive fetch failed: {e}")
        return jobs

    def fetch_greenhouse_boards(self, board_tokens=["stripe", "coinbase", "revolut", "binance", "brex"]):
        jobs = []
        for token in board_tokens:
            try:
                url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
                res = requests.get(url, timeout=8)
                if res.status_code == 200:
                    for item in res.json().get("jobs", []):
                        title = item.get("title", "")
                        location = item.get("location", {}).get("name", "Various")
                        content = item.get("content", "")
                        
                        if self.is_target_role(title, content):
                            is_prio = self.is_priority_location(location)
                            is_sec = self.is_secondary_location(location)
                            
                            if is_prio or is_sec or "worldwide" in location.lower():
                                jobs.append({
                                    "title": title,
                                    "company": token.capitalize(),
                                    "location": location,
                                    "url": item.get("absolute_url"),
                                    "source": f"Greenhouse ({token.capitalize()})",
                                    "workplace_type": self.detect_workplace_type(title, location),
                                    "is_priority": is_prio,
                                    "date": datetime.now().strftime("%Y-%m-%d")
                                })
            except Exception as e:
                print(f"[!] Greenhouse fetch failed for {token}: {e}")
        return jobs

    def run_all(self):
        all_jobs = []
        all_jobs.extend(self.fetch_arbeitnow())
        all_jobs.extend(self.fetch_remotive())
        all_jobs.extend(self.fetch_greenhouse_boards())
        
        seen_urls = set()
        deduped_jobs = []
        for job in all_jobs:
            if job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                deduped_jobs.append(job)
                
        return deduped_jobs