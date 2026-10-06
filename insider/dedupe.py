"""Cross-run dedupe backed by data/seen.json.

Each job gets up to two keys: "<source>:<job_id>" (when the source exposes an ID)
and "url:<normalized apply URL>". A job counts as seen if ANY of its keys is
stored, so changing how one key is built never causes a wave of re-posts.
"""
import json
import os
import re
from datetime import date, timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

DEFAULT_PATH = os.path.join("data", "seen.json")
RETENTION_DAYS = 180

# Query parameters that only track where a click came from; never part of a job's identity.
_TRACKING_PARAMS = {"ref", "referrer", "source", "src", "gh_src", "lever-source", "lever-origin",
                    "utm_id", "fbclid", "gclid", "trk", "trackingid"}


def normalize_url(url):
    """Lowercase scheme/host, drop fragment, tracking params and trailing slash; sort the query.
    Keeps meaningful params such as Greenhouse's ?gh_jid=123."""
    if not url:
        return ""
    parts = urlsplit(url.strip())
    query = sorted(
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if k.lower() not in _TRACKING_PARAMS and not k.lower().startswith("utm_")
    )
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower() or "https", parts.netloc.lower(), path, urlencode(query), ""))


def source_slug(source):
    """'Greenhouse (Stripe)' -> 'greenhouse'."""
    match = re.match(r"[a-z0-9]+", (source or "").lower())
    return match.group(0) if match else "unknown"


def job_keys(job):
    keys = []
    if job.get("job_id"):
        keys.append(f"{source_slug(job.get('source'))}:{job['job_id']}")
    url = normalize_url(job.get("url"))
    if url:
        keys.append(f"url:{url}")
    return keys


class SeenStore:
    def __init__(self, path=DEFAULT_PATH):
        self.path = path
        self.seen = {}  # key -> ISO date first seen
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.seen = json.load(f).get("seen", {})
            except (OSError, ValueError) as e:
                # A corrupt cache must not kill the run; worst case some jobs are re-posted once.
                print(f"[!] Could not read {path} ({e}); starting with an empty seen list.")

    def __len__(self):
        return len(self.seen)

    def is_seen(self, job):
        return any(k in self.seen for k in job_keys(job))

    def mark(self, job):
        today = date.today().isoformat()
        for k in job_keys(job):
            self.seen.setdefault(k, today)

    def save(self):
        cutoff = (date.today() - timedelta(days=RETENTION_DAYS)).isoformat()
        self.seen = {k: d for k, d in self.seen.items() if d >= cutoff}
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "seen": self.seen}, f, indent=0, sort_keys=True)
        os.replace(tmp, self.path)
