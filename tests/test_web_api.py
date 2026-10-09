from urllib.request import Request

import pytest
from fastapi import HTTPException

from api import index
from api.index import health, qualify, search_crm, QualificationRequest, CRMSearchRequest


def test_health_marks_api_as_demo_only():
    assert health() == {"status": "ok", "mode": "demo", "real_integrations": False}


def test_qualification_returns_explainable_score_and_requires_consent_for_hot():
    result = qualify(QualificationRequest(
        need="Looking for a property",
        budget="₹80 lakh",
        timeline="3 months",
        contact_method="phone",
        consent_to_contact=False,
    ))
    assert result["score"] == 75
    assert result["tier"] == "warm"
    assert "consent_to_contact" in result["missing_fields"]
    assert result["mode"] == "rules_based_demo"


def test_crm_search_only_returns_seeded_sample_contacts():
    result = search_crm(CRMSearchRequest(query="Asha"))
    assert result["count"] == 1
    assert result["contacts"][0]["name"] == "Asha Kumar"
    assert result["contacts"][0]["email"].endswith("example.test")


def test_supabase_health_requires_url_and_publishable_key(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        index.supabase_health()
    assert exc.value.status_code == 503


def test_supabase_health_checks_auth_service_without_database_access(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "sb_publishable_test")

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(request, timeout):
        assert isinstance(request, Request)
        assert request.full_url == "https://example.supabase.co/auth/v1/health"
        assert request.get_header("Apikey") == "sb_publishable_test"
        assert timeout == 4
        return FakeResponse()

    monkeypatch.setattr(index, "urlopen", fake_urlopen)
    assert index.supabase_health() == {
        "status": "reachable",
        "database_access": False,
        "mode": "connection_check_only",
    }


def test_supabase_health_rejects_non_https_url(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "http://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "sb_publishable_test")
    with pytest.raises(HTTPException) as exc:
        index.supabase_health()
    assert exc.value.status_code == 503
