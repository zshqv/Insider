import requests
from insider.sources._common import load_companies, format_date, within_recency, detect_workplace, job


def fetch(filter_fn):
    tokens = load_companies().get("greenhouse", [])
    jobs = []
    for token in tokens:
        try:
            url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
            res = requests.get(url, timeout=10)
            if res.status_code != 200:
                continue
            for item in res.json().get("jobs", []):
                title = item.get("title", "")
                loc = item.get("location", {}).get("name", "Various")
                content = item.get("content", "")
                date_posted = format_date(item.get("updated_at"))

                if not filter_fn(title, content) or not within_recency(date_posted):
                    continue

                jobs.append(job(
                    title=title,
                    company=token.capitalize(),
                    location=loc,
                    url=item.get("absolute_url"),
                    source=f"Greenhouse ({token.capitalize()})",
                    job_id=item.get("id"),
                    source_type="Direct Career Portal 🎯",
                    workplace=detect_workplace(title, loc, content),
                    is_priority=False,
                    date_posted=date_posted,
                ))
        except Exception as e:
            print(f"[!] Greenhouse fetch failed for {token}: {e}")
    return jobs
