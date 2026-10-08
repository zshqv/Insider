import requests
from insider.sources._common import format_date, within_recency, job


def fetch(filter_fn):
    jobs = []
    try:
        res = requests.get("https://www.arbeitnow.com/api/job-board-api", timeout=10)
        if res.status_code != 200:
            return jobs
        for item in res.json().get("data", []):
            title = item.get("title", "")
            loc = item.get("location", "")
            desc = item.get("description", "")
            raw_date = item.get("created_at")
            if isinstance(raw_date, (int, float)) and raw_date > 1_000_000_000:
                from datetime import datetime
                date_posted = datetime.utcfromtimestamp(raw_date).strftime("%Y-%m-%d")
            else:
                date_posted = format_date(raw_date)

            if not filter_fn(title, desc) or not within_recency(date_posted):
                continue

            jobs.append(job(
                title=title,
                company=item.get("company_name", "Unknown"),
                location=loc,
                url=item.get("url"),
                source="Arbeitnow",
                job_id=item.get("slug"),
                source_type="Aggregator 📦",
                workplace="Remote 🌐" if item.get("remote") else "On-site 🏢",
                is_priority=False,
                date_posted=date_posted,
                description=desc,
            ))
    except Exception as e:
        print(f"[!] Arbeitnow fetch failed: {e}")
    return jobs
