"""Demo-only API endpoints for the hosted SNA AI Agent Studio.

This API uses deterministic qualification and fictional, in-memory CRM data.
It is not an authenticated production API and must not receive real customer data.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, StrictBool

from core.lead_qualification import LeadProfile, qualify_lead
from core.mock_crm import MockCRM

app = FastAPI(title="SNA AI Agent Studio Demo API", version="0.1.0")
crm = MockCRM()


class QualificationRequest(BaseModel):
    name: str = Field(default="", max_length=200)
    need: str = Field(default="", max_length=2000)
    budget: str = Field(default="", max_length=200)
    timeline: str = Field(default="", max_length=200)
    contact_method: str = Field(default="", max_length=200)
    consent_to_contact: StrictBool = False


class CRMSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=100)


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "demo", "real_integrations": False}


@app.post("/api/qualify")
def qualify(request: QualificationRequest):
    result = qualify_lead(LeadProfile(
        name=request.name,
        need=request.need,
        budget=request.budget,
        timeline=request.timeline,
        contact_method=request.contact_method,
        consent_to_contact=request.consent_to_contact,
    ))
    return {
        "score": result.score,
        "tier": result.tier,
        "reasons": list(result.reasons),
        "missing_fields": list(result.missing_fields),
        "mode": "rules_based_demo",
    }


@app.post("/api/crm/search")
def search_crm(request: CRMSearchRequest):
    try:
        return crm.search_contacts(request.query.strip())
    except Exception:
        raise HTTPException(status_code=400, detail="Unable to search demo contacts.")
