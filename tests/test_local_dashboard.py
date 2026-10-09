from examples.local_dashboard import qualification_from_payload, search_mock_crm
from core.mock_crm import MockCRM
import pytest


def test_dashboard_qualification_requires_explicit_consent_for_contact():
    result = qualification_from_payload({
        "need": "Wants a home",
        "budget": "₹80 lakh",
        "timeline": "Within 3 months",
        "contact_method": "email",
        "consent_to_contact": False,
    })
    assert result["score"] == 75
    assert result["tier"] == "warm"
    assert result["can_contact"] is False
    assert "consent_to_contact" in result["missing_fields"]


def test_dashboard_qualification_accepts_explicit_consent():
    result = qualification_from_payload({
        "need": "Wants a home",
        "budget": "₹80 lakh",
        "timeline": "Within 3 months",
        "contact_method": "email",
        "consent_to_contact": True,
    })
    assert result["tier"] == "hot"
    assert result["can_contact"] is True


def test_dashboard_rejects_wrong_field_types():
    with pytest.raises(ValueError):
        qualification_from_payload({"need": 123})


def test_dashboard_crm_search_is_read_only():
    crm = MockCRM()
    result = search_mock_crm(crm, {"query": "Asha"})
    assert result["count"] == 1
    assert result["contacts"][0]["name"] == "Asha Kumar"
    assert crm.search_contacts("Asha")["count"] == 1


def test_dashboard_rejects_empty_or_long_crm_query():
    with pytest.raises(ValueError):
        search_mock_crm(MockCRM(), {"query": ""})
    with pytest.raises(ValueError):
        search_mock_crm(MockCRM(), {"query": "x" * 101})
