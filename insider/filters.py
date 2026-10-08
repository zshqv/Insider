"""Role filtering and location tiering driven by config/filters.yaml."""

import os
import re
import json
import unicodedata
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


_GENDER_TAG_RE = re.compile(
    r"\(\s*(?:m\s*/\s*w\s*/\s*d|m\s*/\s*f\s*/\s*d|f\s*/\s*m\s*/\s*d|d\s*/\s*f\s*/\s*m|"
    r"all\s+genders|w\s*/\s*m\s*/\s*d|gn)\s*\)",
    re.IGNORECASE,
)


def normalize_title(title):
    """Lowercase, unicode-normalize, strip gender tags, replace punctuation with spaces."""
    t = unicodedata.normalize("NFKD", title)
    t = _GENDER_TAG_RE.sub(" ", t)
    t = re.sub(r"[&/|,()[\]{}\-–—]", " ", t)
    t = t.lower()
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _build_stem_pattern(stems):
    """Build a regex that matches token prefixes: 'engineer' matches engineer, engineers, engineering."""
    parts = []
    for stem in stems:
        escaped = re.escape(stem.lower())
        parts.append(escaped + r"\w*")
    return re.compile(r"\b(?:" + "|".join(parts) + r")\b", re.IGNORECASE)


def build_role_filter(target_roles):
    """Return a (title, description) -> bool that enforces the fixed evaluation order."""
    cfg = _load()
    roles = [normalize_title(r) for r in target_roles]
    block_re = _word_pattern(cfg["seniority_block"])
    noise_re = _word_pattern(cfg.get("noise_block", []))
    eng_re = _build_stem_pattern(cfg.get("engineering_block", []))
    allow_phrases = [p.lower() for p in cfg.get("allow_phrases", [])]
    max_yoe = cfg.get("max_yoe", 2)
    high_yoe_re = re.compile(
        rf"\b({max_yoe + 1}|[{max_yoe + 1}-9]|\d{{2,}})\+?\s*(years?|yrs?|yoe)\b", re.IGNORECASE
    )

    def passes(title, description=""):
        norm = normalize_title(title)
        text = f"{title} {description}".lower()

        eng_match = eng_re.search(norm)
        if eng_match:
            has_allow = any(phrase in norm for phrase in allow_phrases)
            if not has_allow:
                return False

        if noise_re.search(norm):
            return False

        if not any(role in norm for role in roles):
            return False

        if block_re.search(norm):
            return False

        if high_yoe_re.search(text):
            return False

        return True

    return passes


def is_target_role(job, target_roles):
    """Single choke point: returns (verdict: bool, reason: str).

    Every source MUST call this (or build_role_filter which uses the same logic).
    """
    cfg = _load()
    title = job.get("title", "")
    desc = job.get("description", "")
    norm = normalize_title(title)

    roles = [normalize_title(r) for r in target_roles]
    block_re = _word_pattern(cfg["seniority_block"])
    noise_re = _word_pattern(cfg.get("noise_block", []))
    eng_re = _build_stem_pattern(cfg.get("engineering_block", []))
    allow_phrases = [p.lower() for p in cfg.get("allow_phrases", [])]
    max_yoe = cfg.get("max_yoe", 2)
    high_yoe_re = re.compile(
        rf"\b({max_yoe + 1}|[{max_yoe + 1}-9]|\d{{2,}})\+?\s*(years?|yrs?|yoe)\b", re.IGNORECASE
    )
    text = f"{title} {desc}".lower()

    eng_match = eng_re.search(norm)
    has_allow = any(phrase in norm for phrase in allow_phrases) if eng_match else False

    if eng_match and not has_allow:
        return False, f"engineering block: '{eng_match.group()}'"
    if noise_re.search(norm):
        m = noise_re.search(norm)
        return False, f"noise block: '{m.group()}'"
    if not any(role in norm for role in roles):
        return False, "no target role match"
    if block_re.search(norm):
        m = block_re.search(norm)
        return False, f"seniority block: '{m.group()}'"
    if high_yoe_re.search(text):
        return False, "YOE too high"

    if eng_match and has_allow:
        job["_filter_note"] = "engineering stem + analyst phrase: verify"

    return True, "passed"


def explain_filter(title, description, target_roles):
    """Trace the exact production filter path and return a list of (step, detail, result) tuples."""
    cfg = _load()
    roles = [normalize_title(r) for r in target_roles]
    block_re = _word_pattern(cfg["seniority_block"])
    noise_re = _word_pattern(cfg.get("noise_block", []))
    eng_re = _build_stem_pattern(cfg.get("engineering_block", []))
    allow_phrases = [p.lower() for p in cfg.get("allow_phrases", [])]
    max_yoe = cfg.get("max_yoe", 2)
    high_yoe_re = re.compile(
        rf"\b({max_yoe + 1}|[{max_yoe + 1}-9]|\d{{2,}})\+?\s*(years?|yrs?|yoe)\b", re.IGNORECASE
    )

    norm = normalize_title(title)
    text = f"{title} {description}".lower()
    trace = []

    trace.append(("Normalized title", norm, None))

    # Engineering stem block
    m = eng_re.search(norm)
    if m:
        trace.append(("Engineering block", f"MATCHED '{m.group()}' at pos {m.start()}", "HIT"))
        matched_phrases = [p for p in allow_phrases if p in norm]
        if matched_phrases:
            trace.append(("Allow phrases", f"MATCHED phrases: {matched_phrases} — block overridden (quarantine)", "OVERRIDE"))
        else:
            trace.append(("Allow phrases", "no phrase match — engineering block stands", "BLOCKED"))
            return trace, False
    else:
        trace.append(("Engineering block", "no match", "passed"))

    # Noise block
    m = noise_re.search(norm)
    if m:
        trace.append(("Noise block", f"MATCHED '{m.group()}' at pos {m.start()}", "BLOCKED"))
        return trace, False
    trace.append(("Noise block", "no match", "passed"))

    # Positive role match
    matched = [r for r in roles if r in norm]
    if matched:
        trace.append(("Role match", f"MATCHED roles: {matched}", "passed"))
    else:
        trace.append(("Role match", "no target role found in title", "BLOCKED"))
        return trace, False

    # Seniority block
    m = block_re.search(norm)
    if m:
        trace.append(("Seniority block", f"MATCHED '{m.group()}' at pos {m.start()}", "BLOCKED"))
        return trace, False
    trace.append(("Seniority block", "no match", "passed"))

    # YOE
    m = high_yoe_re.search(text)
    if m:
        trace.append(("YOE cap", f"MATCHED '{m.group()}' — too senior", "BLOCKED"))
        return trace, False
    trace.append(("YOE cap", "no match", "passed"))

    trace.append(("Final", "all checks passed", "PASS"))
    return trace, True


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
    """Assign tier (0=high-priority remote, 1=Mumbai, 2=international, 3=pan-India)."""
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
