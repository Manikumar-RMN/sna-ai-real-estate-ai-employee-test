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

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, StrictBool

from core.lead_qualification import LeadProfile, qualify_lead
from core.mock_crm import MockCRM

app = FastAPI(title="SNA AI Agent Studio Demo API", version="0.2.0")
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


def _supabase_read_table(table: str):
    """Read a small, safe projection of tenant-neutral setup records."""
    project_url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    publishable_key = os.environ.get("SUPABASE_ANON_KEY", "").strip()
    parsed = urlparse(project_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or not publishable_key:
        raise HTTPException(status_code=503, detail="Supabase is not configured safely.")

    request = Request(
        f"{project_url}/rest/v1/{table}?select=*&limit=50",
        headers={"apikey": publishable_key, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise HTTPException(status_code=502, detail="Supabase denied table access.")
        raise HTTPException(status_code=502, detail="Supabase table query failed.")
    except (URLError, TimeoutError, OSError, ValueError):
        raise HTTPException(status_code=502, detail="Supabase table query failed.")

    if not isinstance(payload, list):
        raise HTTPException(status_code=502, detail="Supabase returned an unexpected response.")
    # Never forward arbitrary columns (which may include private configuration).
    allowed = {"id", "name", "business_name", "agent_name", "status", "created_at", "updated_at"}
    rows = []
    for item in payload:
        if isinstance(item, dict):
            rows.append({key: item[key] for key in allowed if key in item})
    return {"count": len(rows), "items": rows, "mode": "supabase_read_only"}


@app.get("/api/data/businesses")
def list_businesses():
    """Return up to 50 businesses, exposing only a small field allowlist."""
    return _supabase_read_table("businesses")


@app.get("/api/data/agents")
def list_agents():
    """Return up to 50 agents, exposing only a small field allowlist."""
    return _supabase_read_table("agents")
