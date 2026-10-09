"""Opt-in Gemini and n8n integrations. External calls are disabled unless explicitly enabled server-side."""
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from api.workspace import _authenticated_user, _profile, _request

router = APIRouter(prefix="/api/integrations", tags=["integrations"])
_MODEL_RE = re.compile(r"^[a-zA-Z0-9._-]{1,100}$")


class AgentTask(BaseModel):
    agent_id: UUID
    task: str = Field(min_length=1, max_length=8000)


class WorkflowDispatch(BaseModel):
    event: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_.-]+$")
    payload: dict = Field(default_factory=dict)


def _enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _safe_webhook_url():
    url = os.environ.get("N8N_WEBHOOK_URL", "").strip()
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(status_code=503, detail="n8n webhook URL must be a valid HTTPS URL.")
    return url


@router.get("/status")
def integration_status(authorization: str | None = Header(default=None)):
    """Report readiness without disclosing secrets or calling external services."""
    token, user = _authenticated_user(authorization)
    profile = _profile(token, user["id"])
    if not profile:
        raise HTTPException(status_code=409, detail="Create your workspace before configuring integrations.")
    webhook = _safe_webhook_url()
    return {
        "mode": "opt_in",
        "gemini": {
            "configured": bool(os.environ.get("GEMINI_API_KEY", "").strip()),
            "execution_enabled": _enabled("GEMINI_EXECUTION_ENABLED"),
            "model": os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
        },
        "n8n": {
            "configured": bool(webhook),
            "workflow_execution_enabled": _enabled("N8N_ALLOW_WORKFLOW_EXECUTION"),
        },
        "external_calls_made": False,
    }


@router.post("/gemini/run")
def run_gemini_task(body: AgentTask, authorization: str | None = Header(default=None)):
    """Execute an agent belonging to this workspace, only after operator opt-in."""
    token, user = _authenticated_user(authorization)
    profile = _profile(token, user["id"])
    if not profile:
        raise HTTPException(status_code=409, detail="Create your workspace before running an AI employee.")
    if not _enabled("GEMINI_EXECUTION_ENABLED"):
        raise HTTPException(status_code=503, detail="Gemini execution is disabled. Check the applicable free-tier limits and billing settings before enabling real API calls.")
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="Gemini API key is not configured on the server.")
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()
    if not _MODEL_RE.fullmatch(model):
        raise HTTPException(status_code=503, detail="Gemini model configuration is invalid.")
    agents = _request(
        "/rest/v1/agents?select=id,name,system_prompt,status&business_id=eq."
        + str(profile["business_id"]) + "&id=eq." + str(body.agent_id) + "&limit=1",
        token=token,
    )
    if not isinstance(agents, list) or not agents:
        raise HTTPException(status_code=404, detail="AI employee was not found in this workspace.")
    agent = agents[0]
    if agent.get("status") != "active":
        raise HTTPException(status_code=409, detail="Activate this AI employee before running tasks.")
    prompt = str(agent.get("system_prompt") or "").strip()
    if not prompt:
        raise HTTPException(status_code=409, detail="This AI employee has no instructions configured.")
    request = Request(
        "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent",
        data=json.dumps({
            "systemInstruction": {"parts": [{"text": prompt}]},
            "contents": [{"role": "user", "parts": [{"text": body.task}]}],
            "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.2},
        }).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    try:
        with urlopen(request, timeout=25) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 429:
            raise HTTPException(status_code=429, detail="Gemini rate limit or quota reached.")
        if exc.code in (401, 403):
            raise HTTPException(status_code=502, detail="Gemini rejected the configured credentials or permissions.")
        raise HTTPException(status_code=502, detail="Gemini request failed.")
    except (URLError, TimeoutError, OSError, ValueError):
        raise HTTPException(status_code=502, detail="Gemini is unavailable or returned an invalid response.")
    candidates = result.get("candidates") if isinstance(result, dict) else None
    parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
    answer = "\n".join(p.get("text", "") for p in parts if isinstance(p, dict) and isinstance(p.get("text"), str)).strip()
    if not answer:
        raise HTTPException(status_code=502, detail="Gemini returned no text result.")
    return {"agent_id": str(body.agent_id), "agent_name": agent.get("name"), "result": answer, "provider": "google_gemini", "model": model}


@router.post("/n8n/dispatch")
def dispatch_n8n_workflow(body: WorkflowDispatch, authorization: str | None = Header(default=None)):
    """Dispatch an event only after explicit server-side opt-in; may trigger workflow side effects."""
    token, user = _authenticated_user(authorization)
    profile = _profile(token, user["id"])
    if not profile:
        raise HTTPException(status_code=409, detail="Create your workspace before using integrations.")
    if not _enabled("N8N_ALLOW_WORKFLOW_EXECUTION"):
        raise HTTPException(status_code=503, detail="n8n workflow dispatch is disabled. Review the workflow before explicitly enabling dispatch.")
    webhook = _safe_webhook_url()
    if not webhook:
        raise HTTPException(status_code=503, detail="n8n webhook URL is not configured on the server.")
    data = json.dumps({
        "event": body.event, "payload": body.payload,
        "workspace_id": str(profile["business_id"]), "actor_id": str(user["id"]),
        "source": "sna-ai-agent-studio",
    }).encode("utf-8")
    request = Request(webhook, data=data, headers={"Content-Type": "application/json", "User-Agent": "SNA-AI-Agent-Studio/1.0"}, method="POST")
    try:
        with urlopen(request, timeout=10) as response:
            if not 200 <= response.status < 300:
                raise HTTPException(status_code=502, detail="n8n workflow returned an unsuccessful response.")
        return {"status": "dispatched", "event": body.event, "mode": "external_workflow"}
    except HTTPException:
        raise
    except HTTPError:
        raise HTTPException(status_code=502, detail="n8n webhook rejected the event.")
    except (URLError, TimeoutError, OSError):
        raise HTTPException(status_code=502, detail="n8n webhook is unavailable.")
