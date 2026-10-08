import requests
from insider.sources._common import format_date, within_recency, job
from insider.util import env


ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs"
CATEGORIES = ["accounting-finance-jobs"]
COUNTRIES = ["in", "gb"]


def fetch(filter_fn):
    app_id = env("ADZUNA_APP_ID")
    app_key = env("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        print("[*] Adzuna: ADZUNA_APP_ID / ADZUNA_APP_KEY not set; skipping.")
        return []

    jobs = []
    for country in COUNTRIES:
        for category in CATEGORIES:
            try:
                url = (
                    f"{ADZUNA_BASE}/{country}/search/1"
                    f"?app_id={app_id}&app_key={app_key}"
                    f"&results_per_page=50"
                    f"&category={category}"
                    f"&sort_by=date"
                    f"&max_days_old=30"
                )
                res = requests.get(url, timeout=15)
                if res.status_code != 200:
                    print(f"[!] Adzuna {country}/{category}: HTTP {res.status_code}")
                    continue
                for item in res.json().get("results", []):
                    title = item.get("title", "").replace("<strong>", "").replace("</strong>", "")
                    loc = item.get("location", {}).get("display_name", "Various")
                    desc = item.get("description", "")
                    date_posted = format_date(item.get("created"))

                    if not filter_fn(title, desc) or not within_recency(date_posted):
                        continue

                    jobs.append(job(
                        title=title,
                        company=item.get("company", {}).get("display_name", "Unknown"),
                        location=loc,
                        url=item.get("redirect_url"),
                        source=f"Adzuna ({country.upper()})",
                        job_id=item.get("id"),
                        source_type="Aggregator 📦",
                        workplace="Remote 🌐" if "remote" in f"{title} {loc}".lower() else "On-site 🏢",
                        is_priority=False,
                        date_posted=date_posted,
                        description=desc,
                        desc_quality="snippet",
                    ))
            except Exception as e:
                print(f"[!] Adzuna {country}/{category} fetch failed: {e}")
    return jobs
