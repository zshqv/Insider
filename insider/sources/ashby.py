import re
from html import unescape
from html.parser import HTMLParser

import requests
from insider.sources._common import load_companies, format_date, within_recency, detect_workplace, job


class _StripHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []

    def handle_data(self, data):
        self._parts.append(data)

    def get_text(self):
        return " ".join(self._parts)


def _strip_tags(html):
    if not html or "<" not in html:
        return html or ""
    p = _StripHTML()
    p.feed(unescape(html))
    return p.get_text()


def fetch(filter_fn):
    slugs = load_companies().get("ashby", [])
    jobs = []
    for slug in slugs:
        try:
            url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
            res = requests.get(url, timeout=10)
            if res.status_code != 200:
                continue
            for item in res.json().get("jobs", []):
                title = item.get("title", "")
                loc = item.get("location", "Various")
                date_posted = format_date(item.get("publishedAt"))

                desc = item.get("descriptionPlain", "") or _strip_tags(item.get("description", ""))

                if not filter_fn(title, desc) or not within_recency(date_posted):
                    continue

                apply_url = item.get("jobUrl", f"https://jobs.ashbyhq.com/{slug}/{item.get('id', '')}")

                jobs.append(job(
                    title=title,
                    company=slug.replace("-", " ").title(),
                    location=loc,
                    url=apply_url,
                    source=f"Ashby ({slug.replace('-', ' ').title()})",
                    job_id=item.get("id"),
                    source_type="Direct Career Portal 🎯",
                    workplace=detect_workplace(title, loc, desc),
                    is_priority=False,
                    date_posted=date_posted,
                    description=desc,
                ))
        except Exception as e:
            print(f"[!] Ashby fetch failed for {slug}: {e}")
    return jobs
