import time
from html import unescape
from html.parser import HTMLParser

import requests
import xml.etree.ElementTree as ET
from insider.sources._common import format_date, within_recency, job


WWR_FEED = "https://weworkremotely.com/categories/remote-finance-legal-jobs.rss"
_MAX_ENRICH = 20
_ENRICH_DELAY = 0.5


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


def _enrich(url):
    """Fetch the full WWR posting page and extract body text."""
    try:
        res = requests.get(url, timeout=10, headers={"User-Agent": "InsiderBot/1.0"})
        if res.status_code != 200:
            return ""
        return _strip_tags(res.text)
    except Exception:
        return ""


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
            desc = _strip_tags((item.findtext("description") or "").strip())
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

            quality = "snippet" if len(desc) < 300 else "full"

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
                desc_quality=quality,
            ))
    except Exception as e:
        print(f"[!] WWR fetch failed: {e}")

    enriched = 0
    for j in jobs:
        if j["desc_quality"] != "snippet" or enriched >= _MAX_ENRICH:
            continue
        full = _enrich(j["url"])
        if len(full) > len(j["description"]):
            j["description"] = full
            j["desc_quality"] = "full"
            enriched += 1
            time.sleep(_ENRICH_DELAY)

    if enriched:
        print(f"[*] WWR: enriched {enriched} posting(s) with full description.")

    return jobs
