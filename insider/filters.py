"""Role filtering and location tiering driven by config/filters.yaml."""

import os
import re
import json
import yaml
from datetime import datetime

_FILTERS_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "filters.yaml")
_cfg = None


def _load():
    global _cfg
    if _cfg is None:
        with open(_FILTERS_PATH, "r", encoding="utf-8") as f:
            _cfg = yaml.safe_load(f)
    return _cfg


def _word_pattern(phrases):
    escaped = [re.escape(p) for p in phrases]
    return re.compile(r"\b(?:" + "|".join(escaped) + r")\b", re.IGNORECASE)


def build_role_filter(target_roles):
    """Return a (title, description) -> bool that enforces seniority, noise, and YOE rules."""
    cfg = _load()
    roles = [r.lower() for r in target_roles]
    block_re = _word_pattern(cfg["seniority_block"])
    noise_re = _word_pattern(cfg["noise_block"])
    max_yoe = cfg.get("max_yoe", 2)
    high_yoe_re = re.compile(
        rf"\b({max_yoe + 1}|[{max_yoe + 1}-9]|\d{{2,}})\+?\s*(years?|yrs?|yoe)\b", re.IGNORECASE
    )

    def passes(title, description=""):
        t = title.lower()
        text = f"{title} {description}".lower()
        if block_re.search(t):
            return False
        if noise_re.search(t):
            return False
        if high_yoe_re.search(text):
            return False
        return any(role in t for role in roles)

    return passes


def _is_genuinely_remote(location, description):
    """True only if the job is fully remote with no geo-fence."""
    cfg = _load()
    combined = f"{location} {description}".lower()

    for phrase in cfg.get("remote_geo_fence", []):
        if phrase.lower() in combined:
            return False

    loc_lower = location.lower()
    loc_no_remote = re.sub(r"\bremote\b", "", loc_lower).strip(" -–—/,")
    for region in cfg.get("remote_region_block", []):
        if re.search(r"\b" + re.escape(region) + r"\b", loc_lower):
            return False
        if loc_no_remote and re.search(r"\b" + re.escape(region) + r"\b", loc_no_remote):
            return False

    if loc_no_remote and not any(
        ok in loc_no_remote for ok in (cfg.get("tier1_locations", []) + cfg.get("india_locations", []))
    ):
        if len(loc_no_remote) > 2:
            return False

    return True


def _is_india_location(loc, cfg):
    for place in cfg.get("tier1_locations", []) + cfg.get("india_locations", []):
        if place.lower() in loc:
            return True
    return False


def classify_tier(job):
    """Assign tier (0=high-priority remote, 1=Mumbai, 2=international, 3=pan-India).

    All tiers are posted to Discord.
    """
    cfg = _load()
    loc = job.get("location", "").lower()
    title = job.get("title", "").lower()
    desc = job.get("description", "")
    is_remote = "remote" in f"{title} {loc}"

    if is_remote:
        if _is_genuinely_remote(job.get("location", ""), desc):
            job["tier"] = 0
            job["is_priority"] = True
            _add_badges(job, title, desc)
            return job
        if _is_india_location(loc, cfg):
            job["tier"] = 0
            job["is_priority"] = True
            _add_badges(job, title, desc)
            return job
        job["tier"] = 2
        job["is_priority"] = False
        _add_badges(job, title, desc)
        return job

    for t1 in cfg.get("tier1_locations", []):
        if t1.lower() in loc:
            job["tier"] = 1
            job["is_priority"] = True
            _add_badges(job, title, desc)
            return job

    if _is_india_location(loc, cfg):
        job["tier"] = 3
        job["is_priority"] = False
        _add_badges(job, title, desc)
        return job

    job["tier"] = 2
    job["is_priority"] = False
    _add_badges(job, title, desc)
    return job


def _add_badges(job, title, desc):
    cfg = _load()
    combined = f"{title} {desc}".lower()
    for signal in cfg.get("conversion_signals", []):
        if signal.lower() in combined:
            job["badge"] = "PPO / Conversion 🎓"
            return


def dump_tier3(jobs, path=os.path.join("data", "tier3.jsonl")):
    """Append tier-3 jobs to a JSONL file for later review."""
    if not jobs:
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for j in jobs:
            f.write(json.dumps(j, ensure_ascii=False) + "\n")
    print(f"[*] {len(jobs)} tier-3 job(s) appended to {path}.")
