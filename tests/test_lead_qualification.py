import pytest

from core.config import AgentConfig
from core.lead_qualification import (
    LeadProfile,
    create_lead_qualification_employee,
    qualify_lead,
)
from core.models import ModelResponse
from core.tool_registry import ToolRegistry


def test_qualification_hot_requires_explicit_contact_consent():
    result = qualify_lead(LeadProfile(
        need="Looking for a 3-bedroom home",
        budget="₹80 lakh–₹1 crore",
        timeline="Within 3 months",
        contact_method="email",
        consent_to_contact=True,
    ))
    assert result.score == 100
    assert result.tier == "hot"
    assert result.missing_fields == ()


def test_no_contact_consent_reduces_score_and_is_reported():
    result = qualify_lead(LeadProfile(
        need="Looking for a home",
        budget="Around ₹80 lakh",
        timeline="This year",
        contact_method="email",
        consent_to_contact=False,
    ))
    assert result.score == 75
    assert result.tier == "warm"
    assert "consent_to_contact" in result.missing_fields
    assert not any("consent" in reason.lower() and "provided" in reason.lower()
                   for reason in result.reasons)


def test_empty_profile_is_nurture_with_missing_fields():
    result = qualify_lead(LeadProfile())
    assert result.score == 0
    assert result.tier == "nurture"
    assert set(result.missing_fields) == {
        "need", "budget", "timeline", "contact_method", "consent_to_contact"
    }


def test_invalid_profile_type_is_rejected():
    with pytest.raises(TypeError):
        qualify_lead({"need": "not a dataclass"})


def test_employee_uses_supplied_model_and_defaults_to_read_only():
    class FakeModel:
        def __init__(self):
            self.prompt = ""

        def chat(self, messages, tools):
            self.prompt = messages[0]["content"]
            return ModelResponse(content="Need, budget, and timeline captured.")

    model = FakeModel()
    employee = create_lead_qualification_employee(model, ToolRegistry())
    result = employee.run_result("Qualify this inbound enquiry.")
    assert result.status == "completed"
    assert "Lead Qualification Employee" in model.prompt
    assert "never assume consent" in model.prompt
    assert employee.agent.config.allowed_permissions == {"read"}


def test_caller_can_keep_writes_disabled():
    employee = create_lead_qualification_employee(
        type("Model", (), {"chat": lambda self, messages, tools: ModelResponse(content="ok")})(),
        ToolRegistry(),
        config=AgentConfig(allowed_permissions=set()),
    )
    assert employee.agent.config.allowed_permissions == set()
