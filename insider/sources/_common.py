"""Shared helpers for source modules."""

import os
import yaml
from datetime import datetime, timedelta

_companies = None
COMPANIES_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config", "companies.yaml")


def load_companies():
    global _companies
    if _companies is None:
        with open(COMPANIES_PATH, "r", encoding="utf-8") as f:
            _companies = yaml.safe_load(f)
    return _companies


def format_date(raw):
    """Parse an ISO-ish date string to YYYY-MM-DD. Returns '' if unparseable."""
    if not raw:
        return ""
    try:
        return str(raw).split("T")[0]
    except Exception:
        return ""


def within_recency(date_str, max_days=30):
    if not date_str:
        return True
    try:
        posted = datetime.strptime(date_str, "%Y-%m-%d")
        return posted >= datetime.now() - timedelta(days=max_days)
    except Exception:
        return True


def detect_workplace(title, location, description=""):
    combined = f"{title} {location} {description}".lower()
    if "remote" in combined:
        return "Remote 🌐"
    if "hybrid" in combined:
        return "Hybrid 🏢"
    return "On-site 🏢"


def job(*, title, company, location, url, source, job_id, source_type, workplace, is_priority, date_posted, description="", date_found=None, desc_quality=None):
    """Build a normalised job dict.

    desc_quality: "full" (complete posting), "snippet" (truncated/summary),
                  or None to auto-detect from length.
    """
    if desc_quality is None:
        if not description:
            desc_quality = "title_only"
        elif len(description) < 300:
            desc_quality = "snippet"
        else:
            desc_quality = "full"
    return {
        "title": title,
        "company": company,
        "location": location,
        "url": url,
        "source": source,
        "job_id": job_id,
        "source_type": source_type,
        "workplace_type": workplace,
        "is_priority": is_priority,
        "date_posted": date_posted,
        "description": description,
        "desc_quality": desc_quality,
        "date_found": date_found or datetime.now().strftime("%Y-%m-%d"),
    }
