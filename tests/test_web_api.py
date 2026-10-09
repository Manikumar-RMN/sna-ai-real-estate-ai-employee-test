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
