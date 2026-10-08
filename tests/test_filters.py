"""Filter regression tests — table-driven, covering the stem-based engineering
block, phrase-based allowlist, tightened target roles, and title normalization."""

import json
import os
import pytest
from insider.filters import build_role_filter, normalize_title, is_target_role

TARGET_ROLES = json.load(
    open(os.path.join(os.path.dirname(__file__), "..", "config.json"))
)["target_roles"]


@pytest.fixture
def passes():
    return build_role_filter(TARGET_ROLES)


# ── Must-block titles ────────────────────────────────────────────────────────

MUST_BLOCK = [
    ("Intern AI & Data Engineering (m/f/d)", "stem 'engineer' via 'data engineering'"),
    ("Hardware/Robotics Engineer (Intern or Recent Graduate)", "stem 'hardware'"),
    ("Deployment Engineer (Intern or Recent Graduate)", "stem 'deployment'"),
    ("Software Engineer (Intern or Recent Graduate)", "stem 'software'"),
    ("Firmware Engineer Intern", "stem 'firmware'"),
    ("Mechanical Engineer (Intern)", "stem 'mechanical'"),
    ("Electrical Engineer Graduate", "stem 'electrical'"),
    ("Aviation Engineer Intern", "stem 'aviation engineer'"),
    ("Football Agent - nlpsports", "stem 'football'"),
    ("Airworthiness Consultant - TrustFlight", "stem 'airworthiness'"),
    ("ML Engineer - NLP Team", "stem 'ml engineer'"),
    ("Cloud Engineer Intern", "stem 'cloud engineer'"),
    ("QA Engineer (Junior)", "stem 'qa engineer'"),
    ("DevOps Engineer", "stem 'devops'"),
    ("SRE - Platform Team", "stem 'sre'"),
    ("Backend Developer Intern", "stem 'backend'"),
    ("Frontend Developer (Graduate)", "stem 'frontend'"),
    ("Full Stack Developer", "stem 'full stack'"),
    ("Embedded Systems Engineer", "stem 'embedded'"),
    ("Data Engineer - Analytics Platform", "stem 'data engineer'"),
    ("Trainee Football Agent/Consultant", "stem 'football'"),
    ("Senior Financial Analyst", "seniority block 'senior'"),
    ("VP of Finance", "seniority block 'vp'"),
    ("Head of Compliance", "seniority block 'head of'"),
    ("Marketing Coordinator", "noise block 'marketing'"),
    ("Recruiter - Finance Team", "noise block 'recruiter'"),
    ("Product Manager", "noise block 'product manager'"),
]


class TestMustBlock:
    @pytest.mark.parametrize("title,reason", MUST_BLOCK, ids=[t[0] for t in MUST_BLOCK])
    def test_blocked(self, passes, title, reason):
        assert not passes(title), f"Should block: {reason}"


# ── Must-pass titles ─────────────────────────────────────────────────────────

MUST_PASS = [
    ("Junior Financial Analyst", "exact target role 'financial analyst'"),
    ("Finance Intern", "target role 'finance'"),
    ("Business Analyst Intern", "target role 'business analyst'"),
    ("Data Analyst Intern (m/f/d)", "target role 'data analyst'"),
    ("Operations Analyst", "target role 'operations analyst'"),
    ("Management Trainee - Corporate Finance", "target role 'management trainee'"),
    ("Graduate Consultant - Advisory", "target role 'consultant' + 'advisory'"),
    ("Accounting Associate", "target role 'accounting' + 'associate'"),
    ("Credit Analyst", "target role 'credit analyst'"),
    ("Research Analyst - Equity", "target role 'research analyst'"),
    ("Compliance Associate", "target role 'compliance' + 'associate'"),
    ("FP&A Analyst", "target role 'fp&a'"),
    ("Tax Associate", "target role 'tax' + 'associate'"),
    ("Treasury Coordinator", "target role 'treasury' + 'coordinator'"),
    ("Audit Associate", "target role 'audit' + 'associate'"),
    ("Risk Associate", "target role 'risk' + 'associate'"),
    ("Finance Operations Intern", "target role 'finance'"),
]


class TestMustPass:
    @pytest.mark.parametrize("title,reason", MUST_PASS, ids=[t[0] for t in MUST_PASS])
    def test_passed(self, passes, title, reason):
        assert passes(title), f"Should pass: {reason}"


# ── Quarantine: engineering stem + allow phrase → passes but flagged ──────────

QUARANTINE = [
    "Data Analyst & Automation Engineer",
    "Business Analyst - Software Engineering Team",
]


class TestQuarantine:
    @pytest.mark.parametrize("title", QUARANTINE)
    def test_quarantine_passes(self, passes, title):
        assert passes(title), "Eng stem + allow phrase should pass (quarantine)"

    @pytest.mark.parametrize("title", QUARANTINE)
    def test_quarantine_flagged(self, title):
        job = {"title": title, "description": ""}
        verdict, _ = is_target_role(job, TARGET_ROLES)
        assert verdict
        assert "_filter_note" in job, "Quarantine case should set _filter_note"


# ── Title normalization ──────────────────────────────────────────────────────

class TestNormalization:
    def test_gender_tag_stripped(self):
        assert "m/f/d" not in normalize_title("Analyst (m/f/d)")
        assert "w/m/d" not in normalize_title("Analyst (w/m/d)")

    def test_ampersand_replaced(self):
        assert "&" not in normalize_title("Data & Analytics")

    def test_slash_replaced(self):
        assert "/" not in normalize_title("Finance/Accounting")

    def test_dash_replaced(self):
        n = normalize_title("Entry-Level Analyst")
        assert "-" not in n
        assert "entry level analyst" == n

    def test_whitespace_collapsed(self):
        assert "data analyst" == normalize_title("  Data   Analyst  ")

    def test_unicode_normalized(self):
        n = normalize_title("Bürokauffrau")
        assert len(n) > 0


# ── is_target_role single choke point ────────────────────────────────────────

class TestIsTargetRole:
    def test_returns_reason_on_block(self):
        job = {"title": "Software Engineer Intern", "description": ""}
        verdict, reason = is_target_role(job, TARGET_ROLES)
        assert not verdict
        assert "engineering block" in reason or "software" in reason

    def test_returns_reason_on_pass(self):
        job = {"title": "Financial Analyst", "description": ""}
        verdict, reason = is_target_role(job, TARGET_ROLES)
        assert verdict
        assert reason == "passed"

    def test_no_role_match(self):
        job = {"title": "Zookeeper", "description": ""}
        verdict, reason = is_target_role(job, TARGET_ROLES)
        assert not verdict
        assert "no target role" in reason

    def test_data_alone_does_not_match(self):
        """Standalone 'data' was removed from target_roles."""
        job = {"title": "Data Intern", "description": ""}
        verdict, reason = is_target_role(job, TARGET_ROLES)
        assert not verdict

    def test_intern_alone_does_not_match(self):
        """Standalone 'intern' was removed from target_roles."""
        job = {"title": "Engineering Intern", "description": ""}
        verdict, reason = is_target_role(job, TARGET_ROLES)
        assert not verdict


# ── YOE cap ──────────────────────────────────────────────────────────────────

class TestYOECap:
    def test_3_years_blocked(self, passes):
        assert not passes("Financial Analyst", "3+ years of experience required")

    def test_5_years_blocked(self, passes):
        assert not passes("Consultant", "5 years experience in advisory")

    def test_1_year_passes(self, passes):
        assert passes("Financial Analyst", "1 year of experience preferred")

    def test_2_years_passes(self, passes):
        assert passes("Financial Analyst", "2 years experience")
