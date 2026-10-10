"""Demo API endpoints for the hosted SNA AI Agent Studio.

Lead qualification and CRM search use fictional, in-memory demo data.
The Supabase health endpoint verifies project reachability only; it does not
read or write database records. Do not send real customer data to this demo API.
"""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, StrictBool

from core.lead_qualification import LeadProfile, qualify_lead
from core.mock_crm import MockCRM
from api.workspace import router as workspace_router, _authenticated_user, _profile, _request
from api.integrations import router as integrations_router

app = FastAPI(title="SNA AI Agent Studio Demo API", version="0.2.0")
crm = MockCRM()
app.include_router(workspace_router)
app.include_router(integrations_router)


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


@app.get("/api/supabase/health")
def supabase_health():
    """Check Supabase reachability and read-only access to required tables."""
    project_url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    publishable_key = os.environ.get("SUPABASE_ANON_KEY", "").strip()

    parsed = urlparse(project_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(status_code=503, detail="Supabase URL is not configured safely.")
    if not publishable_key:
        raise HTTPException(status_code=503, detail="Supabase publishable key is not configured.")

    headers = {"apikey": publishable_key, "Accept": "application/json"}
    try:
        health_request = Request(
            f"{project_url}/auth/v1/health",
            headers=headers,
            method="GET",
        )
        with urlopen(health_request, timeout=4) as response:
            if not 200 <= response.status < 300:
                raise HTTPException(status_code=502, detail="Supabase health check failed.")

        # Read-only REST queries verify that the expected tables resolve.
        # RLS may correctly return an empty array; no records are changed.
        checked_tables = []
        for table in ("businesses", "agents"):
            table_request = Request(
                f"{project_url}/rest/v1/{table}?select=id&limit=1",
                headers=headers,
                method="GET",
            )
            with urlopen(table_request, timeout=4) as response:
                if not 200 <= response.status < 300:
                    raise HTTPException(status_code=502, detail="Supabase table access check failed.")
                checked_tables.append(table)

        return {
            "status": "reachable",
            "database_access": True,
            "checked_tables": checked_tables,
            "mode": "read_only_access_check",
        }
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise HTTPException(status_code=502, detail="Supabase rejected the read-only access check.")
        raise HTTPException(status_code=502, detail="Supabase health or table access check failed.")
    except (URLError, TimeoutError, OSError):
        raise HTTPException(status_code=502, detail="Supabase is unreachable.")


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


def _supabase_read_table(table: str, authorization: str | None):
    """Read only the authenticated user's workspace records."""
    if table not in {"businesses", "agents"}:
        raise HTTPException(status_code=404, detail="Data source not found.")
    token, user = _authenticated_user(authorization)
    profile = _profile(token, user["id"])
    if not profile:
        raise HTTPException(status_code=409, detail="Create your workspace before viewing data.")
    business_id = str(profile["business_id"])
    if table == "businesses":
        path = "/rest/v1/businesses?select=id,name,status,created_at&id=eq." + business_id + "&limit=1"
    else:
        path = "/rest/v1/agents?select=id,name,description,status,created_at,updated_at&business_id=eq." + business_id + "&order=created_at.desc&limit=50"
    rows = _request(path, token=token)
    if not isinstance(rows, list):
        raise HTTPException(status_code=502, detail="Supabase returned an unexpected response.")
    return {"count": len(rows), "items": rows, "mode": "authenticated_workspace_read_only"}


@app.get("/api/data/businesses")
def list_businesses(authorization: str | None = Header(default=None)):
    """Return only the authenticated user's workspace."""
    return _supabase_read_table("businesses", authorization)


@app.get("/api/data/agents")
def list_agents(authorization: str | None = Header(default=None)):
    """Return only agents belonging to the authenticated user's workspace."""
    return _supabase_read_table("agents", authorization)
