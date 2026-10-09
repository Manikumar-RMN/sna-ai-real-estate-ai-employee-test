"""Authenticated workspace and AI employee APIs for the test Supabase project."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["workspace"])


class WorkspaceCreate(BaseModel):
    business_name: str = Field(min_length=2, max_length=160)
    full_name: str = Field(min_length=2, max_length=160)


class AgentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=1000)
    system_prompt: str = Field(min_length=10, max_length=8000)
    status: str = Field(default="active", pattern="^(active|inactive)$")


def _config():
    base = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    key = os.environ.get("SUPABASE_ANON_KEY", "").strip()
    parsed = urlparse(base)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or not key:
        raise HTTPException(status_code=503, detail="Supabase is not configured safely.")
    return base, key


def _request(path, token=None, method="GET", payload=None, prefer=None):
    base, key = _config()
    headers = {"apikey": key, "Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if prefer:
        headers["Prefer"] = prefer
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(base + path, headers=headers, data=data, method=method)
    try:
        with urlopen(request, timeout=6) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise HTTPException(status_code=401, detail="Your session is invalid or access is not permitted.")
        if exc.code == 409:
            raise HTTPException(status_code=409, detail="This record already exists.")
        if exc.code == 400:
            raise HTTPException(status_code=400, detail="The submitted data was rejected. Check required fields.")
        raise HTTPException(status_code=502, detail="Supabase request failed.")
    except (URLError, TimeoutError, OSError, ValueError):
        raise HTTPException(status_code=502, detail="Supabase is unavailable or returned an invalid response.")


def _authenticated_user(authorization):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    token = authorization[7:].strip()
    if not token or len(token) > 5000:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    base, key = _config()
    request = Request(base + "/auth/v1/user", headers={
        "apikey": key, "Authorization": "Bearer " + token, "Accept": "application/json"
    })
    try:
        with urlopen(request, timeout=5) as response:
            user = json.loads(response.read().decode("utf-8"))
        if not isinstance(user, dict) or not user.get("id"):
            raise HTTPException(status_code=401, detail="Sign in to continue.")
        return token, user
    except HTTPError:
        raise HTTPException(status_code=401, detail="Your session expired. Please sign in again.")
    except (URLError, TimeoutError, OSError, ValueError):
        raise HTTPException(status_code=502, detail="Could not validate your session.")


def _profile(token, user_id):
    rows = _request(
        "/rest/v1/users?select=id,business_id,name,email,role,status&auth_user_id=eq." + user_id + "&limit=1",
        token=token,
    )
    return rows[0] if rows else None


@router.get("/public-config")
def public_config():
    base, key = _config()
    return {"supabase_url": base, "supabase_publishable_key": key}


@router.get("/workspace")
def get_workspace(authorization: str | None = Header(default=None)):
    token, user = _authenticated_user(authorization)
    profile = _profile(token, user["id"])
    if not profile:
        return {"needs_setup": True, "user": {"id": user["id"], "email": user.get("email")}}
    business_rows = _request(
        "/rest/v1/businesses?select=id,name,status,created_at&id=eq." + profile["business_id"] + "&limit=1",
        token=token,
    )
    agents = _request(
        "/rest/v1/agents?select=id,business_id,name,description,status,created_at,updated_at&business_id=eq."
        + profile["business_id"] + "&order=created_at.desc&limit=100",
        token=token,
    )
    return {
        "needs_setup": False,
        "user": {"id": user["id"], "email": user.get("email"), "name": profile.get("name"), "role": profile.get("role")},
        "business": business_rows[0] if business_rows else None,
        "agents": agents if isinstance(agents, list) else [],
    }


@router.post("/workspace")
def create_workspace(body: WorkspaceCreate, authorization: str | None = Header(default=None)):
    token, user = _authenticated_user(authorization)
    if _profile(token, user["id"]):
        raise HTTPException(status_code=409, detail="A workspace is already linked to this account.")
    rows = _request(
        "/rest/v1/businesses?select=id,name,status",
        token=token, method="POST",
        payload={"name": body.business_name.strip(), "status": "active", "owner_auth_user_id": user["id"]},
        prefer="return=representation",
    )
    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=502, detail="Workspace could not be created.")
    business = rows[0]
    try:
        _request(
            "/rest/v1/users", token=token, method="POST",
            payload={
                "business_id": business["id"], "auth_user_id": user["id"],
                "name": body.full_name.strip(), "email": user.get("email"),
                "role": "owner", "status": "active",
            },
            prefer="return=representation",
        )
    except HTTPException:
        raise HTTPException(status_code=502, detail="Workspace was created but owner setup did not finish. Contact support before retrying.")
    return {"business": business, "status": "created"}


@router.post("/agents")
def create_agent(body: AgentCreate, authorization: str | None = Header(default=None)):
    token, user = _authenticated_user(authorization)
    profile = _profile(token, user["id"])
    if not profile:
        raise HTTPException(status_code=409, detail="Create your workspace before adding an AI employee.")
    rows = _request(
        "/rest/v1/agents", token=token, method="POST",
        payload={
            "business_id": profile["business_id"], "name": body.name.strip(),
            "description": body.description.strip(), "system_prompt": body.system_prompt.strip(),
            "configuration": {"mode": "draft", "provider_configured": False},
            "status": body.status,
        },
        prefer="return=representation",
    )
    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=502, detail="AI employee could not be saved.")
    return {key: rows[0][key] for key in ("id", "business_id", "name", "description", "status", "created_at", "updated_at") if key in rows[0]}


@router.patch("/agents/{agent_id}")
def update_agent(agent_id: UUID, body: AgentCreate, authorization: str | None = Header(default=None)):
    token, user = _authenticated_user(authorization)
    profile = _profile(token, user["id"])
    if not profile:
        raise HTTPException(status_code=409, detail="Create your workspace before editing AI employees.")
    rows = _request(
        "/rest/v1/agents?id=eq." + str(agent_id) + "&business_id=eq." + profile["business_id"],
        token=token, method="PATCH",
        payload={"name": body.name.strip(), "description": body.description.strip(),
                 "system_prompt": body.system_prompt.strip(), "status": body.status},
        prefer="return=representation",
    )
    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=404, detail="AI employee was not found in this workspace.")
    return {key: rows[0][key] for key in ("id", "business_id", "name", "description", "status", "created_at", "updated_at") if key in rows[0]}
