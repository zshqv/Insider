import requests
from insider.sources._common import format_date, within_recency, job


def fetch(filter_fn):
    jobs = []
    try:
        res = requests.get("https://remotive.com/api/remote-jobs?category=finance-legal", timeout=10)
        if res.status_code != 200:
            return jobs
        for item in res.json().get("jobs", []):
            title = item.get("title", "")
            loc = item.get("candidate_required_location", "Worldwide")
            desc = item.get("description", "")
            date_posted = format_date(item.get("publication_date"))

            if not filter_fn(title, desc) or not within_recency(date_posted):
                continue

            jobs.append(job(
                title=title,
                company=item.get("company_name", "Unknown"),
                location=loc,
                url=item.get("url"),
                source="Remotive",
                job_id=item.get("id"),
                source_type="Aggregator 📦",
                workplace="Remote 🌐",
                is_priority=False,
                date_posted=date_posted,
                description=desc,
            ))
    except Exception as e:
        print(f"[!] Remotive fetch failed: {e}")
    return jobs
