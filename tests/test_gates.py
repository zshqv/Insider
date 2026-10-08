"""Gate detection tests — 25+ real-sounding snippets covering German, enrollment, visa, location."""

import pytest
from unittest.mock import patch

# Patch the config before importing gates
_TEST_CANDIDATE = {
    "german_level": "A1",
    "enrolled_student": False,
    "needs_visa_sponsorship": True,
    "based_in": "India",
    "accepts_onsite_in": ["India"],
    "german_posting_assumes_german_required": True,
}

_TEST_CONFIG = {
    "candidate": _TEST_CANDIDATE,
    "tier1_locations": ["mumbai"],
    "india_locations": ["india", "bangalore", "pune"],
    "remote_geo_fence": ["must be based in"],
    "remote_region_block": ["us", "uk", "germany", "europe"],
    "fit": {"post_fit_c": False},
}


@pytest.fixture(autouse=True)
def _mock_config():
    import insider.gates as g
    g._cfg = _TEST_CONFIG
    yield
    g._cfg = None


from insider.gates import detect_german, detect_enrollment, detect_visa, detect_location_gate, apply_gates, compute_fit


# ── German gate ──────────────────────────────────────────────────────────────

class TestGermanGate:
    def test_explicit_c1_required(self):
        level, hard, gate, _ = detect_german("Finance Analyst", "Wir erwarten verhandlungssicheres Deutsch (C1) in Wort und Schrift.")
        assert level == "C1" and hard and gate == "Fail"

    def test_explicit_b2_near_deutsch(self):
        level, hard, gate, _ = detect_german("Buchhalter", "Deutsch B2 erforderlich")
        assert level == "B2" and hard and gate == "Fail"

    def test_soft_von_vorteil_does_not_fail(self):
        level, hard, gate, _ = detect_german("Junior Analyst", "Deutschkenntnisse B2 von Vorteil, Englisch ist Arbeitssprache.")
        assert gate == "Pass" and not hard

    def test_soft_nice_to_have_does_not_fail(self):
        level, hard, gate, _ = detect_german("Accountant", "German B1 nice to have")
        assert gate == "Pass" and not hard

    def test_gute_deutschkenntnisse_fails_at_a1(self):
        level, hard, gate, _ = detect_german("Controller", "Gute Deutschkenntnisse werden vorausgesetzt.")
        assert level == "B2" and gate == "Fail"

    def test_sehr_gute_deutschkenntnisse(self):
        level, hard, gate, _ = detect_german("Analyst", "Sehr gute Deutschkenntnisse in Wort und Schrift")
        assert level == "C1" and gate == "Fail"

    def test_fluent_german(self):
        level, hard, gate, _ = detect_german("Risk Analyst", "Fluent German and English required")
        assert level == "C1" and gate == "Fail"

    def test_good_german(self):
        level, hard, gate, _ = detect_german("Treasury", "Good German language skills needed")
        assert level == "B2" and gate == "Fail"

    def test_basic_german_passes_at_a1(self):
        """A1 candidate meets A2 'basic German' — still fails since A1 < A2."""
        level, hard, gate, _ = detect_german("Intern", "Basic German is a plus")
        assert gate == "Pass"  # soft marker "a plus"

    def test_basic_german_hard_fails(self):
        level, hard, gate, _ = detect_german("Intern", "Basic German required for daily communication")
        assert level == "A2" and gate == "Fail"

    def test_confident_in_german(self):
        level, hard, gate, _ = detect_german("Analyst", "You should be confident in German communication")
        assert level == "B2" and gate == "Fail"

    def test_german_language_posting_fails(self):
        german_text = (
            "Wir suchen einen engagierten Mitarbeiter für unser Team in der Buchhaltung. "
            "Sie sind verantwortlich für die Erstellung von Monatsabschlüssen und die "
            "Überwachung der Kreditoren und Debitoren. Eine abgeschlossene kaufmännische "
            "Ausbildung wird vorausgesetzt. Wir bieten ein dynamisches Arbeitsumfeld "
            "mit flexiblen Arbeitszeiten und attraktiver Vergütung."
        )
        _, _, gate, reason = detect_german("Buchhalter (m/w/d)", german_text)
        assert gate == "Fail" and "German-language posting" in reason

    def test_english_posting_passes(self):
        _, _, gate, _ = detect_german("Junior Analyst", "We are looking for a junior financial analyst to join our team in Mumbai.")
        assert gate == "Pass"

    def test_no_description_unknown(self):
        _, _, gate, _ = detect_german("Finance Intern", "")
        assert gate == "Unknown"

    def test_preferred_wuenschenswert(self):
        _, hard, gate, _ = detect_german("Analyst", "Deutsch C1 wünschenswert")
        assert gate == "Pass" and not hard

    def test_native_german(self):
        level, hard, gate, _ = detect_german("Consultant", "Native German speaker preferred for client communication")
        assert gate == "Pass"  # "preferred" is soft

    def test_muttersprachlich_hard(self):
        level, hard, gate, _ = detect_german("Berater", "Muttersprachlich Deutsch erforderlich")
        assert level == "C1" and gate == "Fail"

    def test_fliessend(self):
        level, _, gate, _ = detect_german("Controller", "Fließend in Deutsch und Englisch")
        assert level == "C1" and gate == "Fail"

    def test_grundkenntnisse(self):
        level, _, gate, _ = detect_german("Trainee", "Grundkenntnisse in Deutsch sind Voraussetzung")
        assert level == "A2" and gate == "Fail"

    def test_sicher_auf_deutsch_kommunizieren(self):
        level, _, gate, _ = detect_german("Risk", "Sie können sicher auf Deutsch kommunizieren")
        assert level == "B2" and gate == "Fail"

    def test_business_fluent_german(self):
        level, _, gate, _ = detect_german("Analyst", "Business fluent German required")
        assert level == "C1" and gate == "Fail"


# ── Enrollment gate ──────────────────────────────────────────────────────────

class TestEnrollmentGate:
    def test_werkstudent_fails(self):
        req, gate, _ = detect_enrollment("Werkstudent Controlling (m/w/d)", "Join our team as Werkstudent")
        assert req == "Yes" and gate == "Fail"

    def test_working_student_fails(self):
        req, gate, _ = detect_enrollment("Working Student Finance", "")
        assert req == "Yes" and gate == "Fail"

    def test_currently_enrolled_fails(self):
        _, gate, _ = detect_enrollment("Intern", "You must be currently enrolled in a degree program")
        assert gate == "Fail"

    def test_pflichtpraktikum_fails(self):
        _, gate, _ = detect_enrollment("Praktikant", "Pflichtpraktikum im Bereich Finance")
        assert gate == "Fail"

    def test_normal_intern_passes(self):
        _, gate, _ = detect_enrollment("Finance Intern", "We're looking for a summer intern to help with reporting.")
        assert gate == "Pass"


# ── Visa gate ────────────────────────────────────────────────────────────────

class TestVisaGate:
    def test_no_sponsorship_fails(self):
        _, gate, _ = detect_visa("Analyst", "No visa sponsorship available for this role")
        assert gate == "Fail"

    def test_must_have_right_to_work_fails(self):
        _, gate, _ = detect_visa("Analyst", "You must have the right to work in the UK")
        assert gate == "Fail"

    def test_visa_sponsorship_available_passes(self):
        offered, gate, _ = detect_visa("Analyst", "Visa sponsorship available for the right candidate")
        assert offered == "Yes" and gate == "Pass"

    def test_relocation_package_passes(self):
        offered, gate, _ = detect_visa("Analyst", "We offer a relocation package for international hires")
        assert offered == "Yes" and gate == "Pass"

    def test_no_mention_unknown(self):
        _, gate, _ = detect_visa("Analyst", "Great opportunity in our London office")
        assert gate == "Unknown"


# ── Location gate ────────────────────────────────────────────────────────────

class TestLocationGate:
    def test_remote_tier0_passes(self):
        gate, _ = detect_location_gate({"tier": 0, "title": "Analyst", "location": "Remote", "description": ""})
        assert gate == "Pass"

    def test_mumbai_passes(self):
        gate, _ = detect_location_gate({"tier": 1, "title": "Analyst", "location": "Mumbai, India", "description": ""})
        assert gate == "Pass"

    def test_london_onsite_fails(self):
        gate, _ = detect_location_gate({"tier": 2, "title": "Analyst", "location": "London, UK", "description": ""})
        assert gate == "Fail"

    def test_onsite_abroad_with_relocation_unknown(self):
        gate, _ = detect_location_gate({
            "tier": 2, "title": "Analyst", "location": "Berlin, Germany",
            "description": "We offer a relocation package"
        })
        assert gate == "Unknown"

    def test_india_onsite_passes(self):
        gate, _ = detect_location_gate({"tier": 3, "title": "Analyst", "location": "Bangalore, India", "description": ""})
        assert gate == "Pass"


# ── Integration: apply_gates + compute_fit ───────────────────────────────────

class TestIntegration:
    def test_clean_remote_job_fit_a(self):
        j = {
            "title": "Junior Financial Analyst",
            "description": "Remote role, visa sponsorship available. Analyze financial data.",
            "location": "Remote",
            "tier": 0,
        }
        apply_gates(j)
        compute_fit(j, ["analyst", "finance"])
        assert j["gate_pass"] == "Pass"
        assert j["fit"] == "A"

    def test_no_visa_info_fit_b(self):
        j = {
            "title": "Junior Financial Analyst",
            "description": "Remote role, we hire globally. Analyze financial data.",
            "location": "Remote",
            "tier": 0,
        }
        apply_gates(j)
        compute_fit(j, ["analyst", "finance"])
        assert j["gate_pass"] == "Unknown"
        assert j["fit"] == "B"

    def test_german_required_fit_b(self):
        j = {
            "title": "Finance Analyst",
            "description": "Fluent German required. Remote role.",
            "location": "Remote",
            "tier": 0,
        }
        apply_gates(j)
        compute_fit(j, ["analyst", "finance"])
        assert j["gate_pass"] == "Fail"
        assert j["fit"] == "B"  # one gate fail + role match

    def test_multiple_fails_fit_c(self):
        j = {
            "title": "Werkstudent Controlling",
            "description": "Fließend Deutsch. Must have right to work in Germany.",
            "location": "Berlin, Germany",
            "tier": 2,
        }
        apply_gates(j)
        compute_fit(j, ["analyst", "finance"])
        assert j["gate_pass"] == "Fail"
        assert j["fit"] == "C"  # multiple fails + no role match

    def test_gate_confidence_full(self):
        j = {
            "title": "Analyst",
            "description": "A" * 500,
            "location": "Remote",
            "tier": 0,
            "desc_quality": "full",
        }
        apply_gates(j)
        assert j["gate_confidence"] == "Full text"

    def test_gate_confidence_snippet(self):
        j = {
            "title": "Analyst",
            "description": "Short desc",
            "location": "Remote",
            "tier": 0,
            "desc_quality": "snippet",
        }
        apply_gates(j)
        assert j["gate_confidence"] == "Snippet only"

    def test_gate_confidence_title_only(self):
        j = {
            "title": "Analyst",
            "description": "",
            "location": "Remote",
            "tier": 0,
        }
        apply_gates(j)
        assert j["gate_confidence"] == "Title only"

    def test_unknown_gate_caps_fit_at_b(self):
        """Even with role match, any Unknown gate keeps Fit at B."""
        j = {
            "title": "Junior Financial Analyst",
            "description": "Great remote opportunity. We hire globally.",
            "location": "Remote",
            "tier": 0,
        }
        apply_gates(j)
        compute_fit(j, ["analyst", "finance"])
        assert j["visa_gate"] == "Unknown"
        assert j["fit"] == "B"  # visa unknown caps at B
