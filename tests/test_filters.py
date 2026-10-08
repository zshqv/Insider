"""Filter logic tests — specifically for the noise/engineering block vs intern override."""

import pytest
from insider.filters import build_role_filter

TARGET_ROLES = [
    "intern", "internship", "analyst", "associate", "finance",
    "consultant", "operations", "trainee", "graduate", "data",
    "automation", "business analyst",
]


@pytest.fixture
def passes():
    return build_role_filter(TARGET_ROLES)


class TestNoiseBlockPrecedence:
    def test_hardware_robotics_intern_blocked(self, passes):
        assert not passes("Hardware/Robotics Engineer (Intern or Recent Graduate)")

    def test_deployment_engineer_intern_blocked(self, passes):
        assert not passes("Deployment Engineer (Intern or Recent Graduate)")

    def test_firmware_intern_blocked(self, passes):
        assert not passes("Firmware Engineer Intern")

    def test_football_agent_blocked(self, passes):
        assert not passes("Football Agent - nlpsports")

    def test_aviation_engineer_blocked(self, passes):
        assert not passes("Aviation Engineer Intern")

    def test_trustflight_consultant_blocked(self, passes):
        assert not passes("Airworthiness Consultant - TrustFlight")

    def test_mechanical_engineer_intern_blocked(self, passes):
        assert not passes("Mechanical Engineer (Intern)")

    def test_electrical_engineer_blocked(self, passes):
        assert not passes("Electrical Engineer Graduate")

    def test_software_engineer_intern_blocked(self, passes):
        assert not passes("Software Engineer (Intern or Recent Graduate)")


class TestFinanceOverridePassesThrough:
    def test_data_analyst_automation_engineer_passes(self, passes):
        assert passes("Data Analyst & Automation Engineer")

    def test_business_analyst_intern_passes(self, passes):
        assert passes("Business Analyst Intern")

    def test_finance_operations_intern_passes(self, passes):
        assert passes("Finance Operations Intern")

    def test_data_engineer_with_analytics_passes(self, passes):
        assert passes("Data Analytics Intern")

    def test_plain_finance_intern_passes(self, passes):
        assert passes("Finance Intern")

    def test_operations_analyst_passes(self, passes):
        assert passes("Operations Analyst")
