"""Source registry — every fetch_* function returns a list of normalised job dicts."""

from insider.sources.greenhouse import fetch as _gh
from insider.sources.lever import fetch as _lever
from insider.sources.ashby import fetch as _ashby
from insider.sources.remotive import fetch as _remotive
from insider.sources.arbeitnow import fetch as _arbeitnow
from insider.sources.wwr import fetch as _wwr
from insider.sources.adzuna import fetch as _adzuna

_SOURCES = [
    ("Greenhouse", _gh),
    ("Lever", _lever),
    ("Ashby", _ashby),
    ("Remotive", _remotive),
    ("Arbeitnow", _arbeitnow),
    ("WWR", _wwr),
    ("Adzuna", _adzuna),
]


def fetch_all(filter_fn):
    """Run every source, apply *filter_fn(title, description) -> bool*, return (jobs, counts).

    *counts* is a dict mapping source name to the number of jobs that passed filters.
    """
    all_jobs = []
    counts = {}
    for name, fetcher in _SOURCES:
        try:
            jobs = fetcher(filter_fn)
        except Exception as e:
            print(f"[!] {name} source failed: {e}")
            jobs = []
        counts[name] = len(jobs)
        all_jobs.extend(jobs)
    return all_jobs, counts
