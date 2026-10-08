"""Gate detection — deterministic keyword/regex checks, no LLM calls.

Each gate evaluates to Pass / Fail / Unknown per job. The combined gate_pass
is Pass only when every gate passes, Fail if any fails, else Unknown.
"""

import os
import re
import yaml

_FILTERS_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "filters.yaml")
_cfg = None

_LEVEL_ORDER = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}

_GERMAN_STOPWORDS = {
    "und", "der", "die", "das", "ist", "in", "den", "von", "zu", "für",
    "mit", "auf", "des", "ein", "eine", "an", "sich", "nicht", "als",
    "auch", "es", "bei", "nach", "aus", "oder", "werden", "wir", "sind",
    "hat", "haben", "wird", "wie", "über", "so", "zum", "zur", "im",
    "dass", "sie", "er", "einem", "einer", "eines", "uns", "dem",
    "noch", "vor", "kann", "dein", "deine", "ihr", "ihre", "du",
    "wenn", "was", "alle", "dich", "aber", "nur", "diese", "dieser",
    "dieses", "mehr", "unter", "ohne", "durch", "vom", "seine", "bis",
}

_SOFT_MARKERS = re.compile(
    r"\b(?:von\s+vorteil|wünschenswert|nice\s+to\s+have|a\s+plus|preferred|ideally|optional|vorteilhaft|hilfreich)\b",
    re.IGNORECASE,
)

_EXPLICIT_LEVEL_RE = re.compile(
    r"\b(A1|A2|B1|B2|C1|C2)\b.*?\b(?:Deutsch|German)\b"
    r"|\b(?:Deutsch|German)\b.*?\b(A1|A2|B1|B2|C1|C2)\b",
    re.IGNORECASE,
)

_GERMAN_PHRASES = [
    (re.compile(r"\b(?:verhandlungssicher|fließend|muttersprachlich)\b", re.I), "C1"),
    (re.compile(r"\b(?:native|business\s+fluent)\b.*?\b(?:German|Deutsch)\b|\b(?:German|Deutsch)\b.*?\b(?:native|business\s+fluent)\b", re.I), "C1"),
    (re.compile(r"\bsehr\s+gute\s+Deutschkenntnisse\b", re.I), "C1"),
    (re.compile(r"\bfluent\s+(?:in\s+)?German\b", re.I), "C1"),
    (re.compile(r"\bgute\s+Deutschkenntnisse\b", re.I), "B2"),
    (re.compile(r"\bgood\s+German\b", re.I), "B2"),
    (re.compile(r"\bsicher\s+auf\s+Deutsch\s+kommunizieren\b", re.I), "B2"),
    (re.compile(r"\bconfident\s+in\s+German\b", re.I), "B2"),
    (re.compile(r"\bGrundkenntnisse\b", re.I), "A2"),
    (re.compile(r"\bbasic\s+German\b", re.I), "A2"),
]

_ENROLLMENT_RE = re.compile(
    r"\b(?:Werkstudent|working\s+student|immatrikuliert|eingeschrieben"
    r"|currently\s+enrolled|student\s+status|mandatory\s+internship|Pflichtpraktikum)\b",
    re.IGNORECASE,
)

_VISA_NO_SPONSOR_RE = re.compile(
    r"\b(?:must\s+have\s+(?:the\s+)?right\s+to\s+work|EU\s+work\s+authoriz?ation"
    r"|no\s+(?:visa\s+)?sponsorship|(?:visa\s+)?sponsorship\s+(?:is\s+)?not\s+available"
    r"|authorized?\s+to\s+work|work\s+permit\s+required"
    r"|legally\s+authoriz?ed|existing\s+(?:right|authorization|permit)\s+to\s+work)\b",
    re.IGNORECASE,
)

_VISA_SPONSOR_YES_RE = re.compile(
    r"\b(?:visa\s+sponsorship(?:\s+(?:available|provided|offered))?|relocation\s+(?:package|support|assistance)"
    r"|we\s+(?:sponsor|provide)\s+(?:visa|work\s+permit))\b",
    re.IGNORECASE,
)


def _load():
    global _cfg
    if _cfg is None:
        with open(_FILTERS_PATH, "r", encoding="utf-8") as f:
            _cfg = yaml.safe_load(f)
    return _cfg


def _candidate():
    return _load().get("candidate", {})


def _level_ge(a, b):
    return _LEVEL_ORDER.get(a.upper(), 0) >= _LEVEL_ORDER.get(b.upper(), 0)


def _is_mostly_german(text):
    words = re.findall(r"[a-zäöüß]+", text.lower())
    if len(words) < 20:
        return False
    german_count = sum(1 for w in words if w in _GERMAN_STOPWORDS)
    return german_count / len(words) > 0.12


def _find_soft_context(text, match_start, match_end):
    window = text[max(0, match_start - 80):min(len(text), match_end + 80)]
    return bool(_SOFT_MARKERS.search(window))


def detect_german(title, description):
    """Returns (required_level or None, is_hard_requirement, gate, reason)."""
    cand = _candidate()
    my_level = cand.get("german_level", "none")
    text = f"{title} {description}"

    found_level = None
    is_hard = True

    for m in _EXPLICIT_LEVEL_RE.finditer(text):
        level = m.group(1) or m.group(2)
        if level:
            found_level = level.upper()
            is_hard = not _find_soft_context(text, m.start(), m.end())
            break

    if not found_level:
        for pattern, level in _GERMAN_PHRASES:
            m = pattern.search(text)
            if m:
                found_level = level
                is_hard = not _find_soft_context(text, m.start(), m.end())
                break

    if found_level:
        if not is_hard:
            return found_level, False, "Pass", f"German {found_level} preferred (soft)"
        if my_level.lower() == "none" or not _level_ge(my_level, found_level):
            return found_level, True, "Fail", f"German {found_level} required"
        return found_level, True, "Pass", ""

    if cand.get("german_posting_assumes_german_required", False) and _is_mostly_german(description):
        return None, True, "Fail", "German-language posting"

    if not description:
        return None, False, "Unknown", "No description available"

    return None, False, "Pass", ""


def detect_enrollment(title, description):
    """Returns (enrollment_required: Yes/No/Unknown, gate, reason)."""
    cand = _candidate()
    text = f"{title} {description}"
    if _ENROLLMENT_RE.search(text):
        if not cand.get("enrolled_student", False):
            return "Yes", "Fail", "Enrollment required"
        return "Yes", "Pass", ""
    if not description:
        return "Unknown", "Unknown", ""
    return "No", "Pass", ""


def detect_visa(title, description):
    """Returns (sponsorship_offered: Yes/No/Unknown, gate, reason)."""
    cand = _candidate()
    text = f"{title} {description}"

    if not cand.get("needs_visa_sponsorship", False):
        if _VISA_SPONSOR_YES_RE.search(text):
            return "Yes", "Pass", ""
        if _VISA_NO_SPONSOR_RE.search(text):
            return "No", "Pass", ""
        return "Unknown", "Pass", ""

    no_match = _VISA_NO_SPONSOR_RE.search(text)
    yes_match = _VISA_SPONSOR_YES_RE.search(text)
    if no_match and yes_match:
        if no_match.start() < yes_match.start():
            return "No", "Fail", "No visa sponsorship"
        return "Yes", "Pass", ""
    if no_match:
        return "No", "Fail", "No visa sponsorship"
    if yes_match:
        return "Yes", "Pass", ""
    if not description:
        return "Unknown", "Unknown", ""
    return "Unknown", "Unknown", ""


def detect_location_gate(job):
    """Returns (gate, reason). Reuses existing tier classification."""
    cand = _candidate()
    tier = job.get("tier")
    accepts = [c.lower() for c in cand.get("accepts_onsite_in", [])]
    loc = job.get("location", "").lower()
    based_in = cand.get("based_in", "").lower()

    if tier == 0:
        return "Pass", ""

    is_remote = "remote" in f"{job.get('title', '')} {loc}".lower()
    if is_remote:
        return "Pass", ""

    for country in accepts:
        if country in loc:
            return "Pass", ""

    if based_in and based_in in loc:
        return "Pass", ""

    desc = job.get("description", "")
    if _VISA_SPONSOR_YES_RE.search(desc):
        return "Unknown", "On-site abroad; relocation offered"

    return "Fail", "On-site outside accepted locations"


def apply_gates(job):
    """Run all gates on a job dict, mutating it with gate fields. Returns job."""
    title = job.get("title", "")
    desc = job.get("description", "")

    german_level, german_hard, german_gate, german_reason = detect_german(title, desc)
    enroll_req, enroll_gate, enroll_reason = detect_enrollment(title, desc)
    visa_offered, visa_gate, visa_reason = detect_visa(title, desc)
    loc_gate, loc_reason = detect_location_gate(job)

    gates = [german_gate, enroll_gate, visa_gate, loc_gate]
    reasons = [r for r in [german_reason, enroll_reason, visa_reason, loc_reason] if r]

    if "Fail" in gates:
        gate_pass = "Fail"
    elif all(g == "Pass" for g in gates):
        gate_pass = "Pass"
    else:
        gate_pass = "Unknown"

    job["german_required"] = german_level
    job["german_hard"] = german_hard
    job["german_gate"] = german_gate
    job["enrollment_required"] = enroll_req
    job["enrollment_gate"] = enroll_gate
    job["visa_sponsorship"] = visa_offered
    job["visa_gate"] = visa_gate
    job["location_gate"] = loc_gate
    job["gate_pass"] = gate_pass
    job["gate_fail_reasons"] = "; ".join(reasons)

    return job


def compute_fit(job, target_roles):
    """Assign fit grade A/B/C based on gates and role match."""
    title = job.get("title", "").lower()
    role_match = any(r.lower() in title for r in target_roles)
    gate_pass = job.get("gate_pass", "Unknown")

    gates = [job.get("german_gate"), job.get("enrollment_gate"),
             job.get("visa_gate"), job.get("location_gate")]
    fail_count = gates.count("Fail")

    if gate_pass == "Pass" and role_match:
        job["fit"] = "A"
    elif (fail_count == 1 and role_match) or gate_pass == "Unknown":
        job["fit"] = "B"
    else:
        job["fit"] = "C"

    return job
