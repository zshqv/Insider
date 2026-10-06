import requests
from insider.sources._common import load_companies, format_date, within_recency, detect_workplace, job


def fetch(filter_fn):
    slugs = load_companies().get("lever", [])
    jobs = []
    for slug in slugs:
        try:
            url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
            res = requests.get(url, timeout=10)
            if res.status_code != 200:
                continue
            for item in res.json():
                title = item.get("text", "")
                loc = item.get("categories", {}).get("location", "Various")
                desc = item.get("descriptionPlain", "")
                created_ms = item.get("createdAt", 0)
                date_posted = format_date(None)
                if created_ms:
                    from datetime import datetime
                    date_posted = datetime.utcfromtimestamp(created_ms / 1000).strftime("%Y-%m-%d")

                if not filter_fn(title, desc) or not within_recency(date_posted):
                    continue

                jobs.append(job(
                    title=title,
                    company=slug.replace("-", " ").title(),
                    location=loc,
                    url=item.get("hostedUrl"),
                    source=f"Lever ({slug.replace('-', ' ').title()})",
                    job_id=item.get("id"),
                    source_type="Direct Career Portal 🎯",
                    workplace=detect_workplace(title, loc, desc),
                    is_priority=False,
                    date_posted=date_posted,
                ))
        except Exception as e:
            print(f"[!] Lever fetch failed for {slug}: {e}")
    return jobs
