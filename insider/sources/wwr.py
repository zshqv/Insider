import requests
import xml.etree.ElementTree as ET
from insider.sources._common import format_date, within_recency, job


WWR_FEED = "https://weworkremotely.com/categories/remote-finance-legal-jobs.rss"


def fetch(filter_fn):
    jobs = []
    try:
        res = requests.get(WWR_FEED, timeout=10)
        if res.status_code != 200:
            return jobs
        root = ET.fromstring(res.content)
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = (item.findtext("description") or "").strip()
            pub = item.findtext("pubDate") or ""

            date_posted = format_date(None)
            if pub:
                from email.utils import parsedate_to_datetime
                try:
                    date_posted = parsedate_to_datetime(pub).strftime("%Y-%m-%d")
                except Exception:
                    pass

            company = "Unknown"
            if ":" in title:
                company, title = title.split(":", 1)
                company = company.strip()
                title = title.strip()

            if not filter_fn(title, desc) or not within_recency(date_posted):
                continue

            jobs.append(job(
                title=title,
                company=company,
                location="Remote",
                url=link,
                source="WeWorkRemotely",
                job_id=link,
                source_type="Aggregator 📦",
                workplace="Remote 🌐",
                is_priority=False,
                date_posted=date_posted,
                description=desc,
            ))
    except Exception as e:
        print(f"[!] WWR fetch failed: {e}")
    return jobs
