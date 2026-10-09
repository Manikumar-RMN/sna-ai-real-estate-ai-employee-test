import json
from urllib.request import Request

import pytest
from fastapi import HTTPException

from api import integrations


def auth(monkeypatch, profile=None):
    monkeypatch.setattr(integrations, "_authenticated_user", lambda authorization: ("user-token", {"id": "user-1", "email": "owner@example.test"}))
    monkeypatch.setattr(integrations, "_profile", lambda token, user_id: profile or {"business_id": "business-1"})


def test_status_never_calls_providers_or_returns_secrets(monkeypatch):
    auth(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "super-secret-test-key")
    monkeypatch.setenv("N8N_WEBHOOK_URL", "https://example.test/webhook")
    result = integrations.integration_status("Bearer user-token")
    assert result["gemini"]["configured"] is True
    assert result["n8n"]["configured"] is True
    assert result["external_calls_made"] is False
    assert "super-secret-test-key" not in json.dumps(result)


def test_gemini_execution_is_disabled_by_default(monkeypatch):
    auth(monkeypatch)
    monkeypatch.delenv("GEMINI_EXECUTION_ENABLED", raising=False)
    with pytest.raises(HTTPException) as exc:
        integrations.run_gemini_task(integrations.AgentTask(agent_id="11111111-1111-4111-8111-111111111111", task="Summarise this test"), authorization="Bearer user-token")
    assert exc.value.status_code == 503
    assert "disabled" in exc.value.detail.lower()


def test_gemini_requires_server_key_even_when_enabled(monkeypatch):
    auth(monkeypatch)
    monkeypatch.setenv("GEMINI_EXECUTION_ENABLED", "true")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        integrations.run_gemini_task(integrations.AgentTask(agent_id="11111111-1111-4111-8111-111111111111", task="Summarise this test"), authorization="Bearer user-token")
    assert exc.value.status_code == 503


def test_gemini_rejects_agent_outside_workspace(monkeypatch):
    auth(monkeypatch)
    monkeypatch.setenv("GEMINI_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-test-key")
    monkeypatch.setattr(integrations, "_request", lambda *args, **kwargs: [])
    with pytest.raises(HTTPException) as exc:
        integrations.run_gemini_task(integrations.AgentTask(agent_id="11111111-1111-4111-8111-111111111111", task="Summarise this test"), authorization="Bearer user-token")
    assert exc.value.status_code == 404


def test_n8n_dispatch_is_disabled_by_default(monkeypatch):
    auth(monkeypatch)
    monkeypatch.setenv("N8N_WEBHOOK_URL", "https://example.test/webhook")
    monkeypatch.delenv("N8N_ALLOW_WORKFLOW_EXECUTION", raising=False)
    with pytest.raises(HTTPException) as exc:
        integrations.dispatch_n8n_workflow(integrations.WorkflowDispatch(event="lead.qualified", payload={"lead_id": "demo"}), authorization="Bearer user-token")
    assert exc.value.status_code == 503


def test_n8n_requires_https_webhook(monkeypatch):
    auth(monkeypatch)
    monkeypatch.setenv("N8N_ALLOW_WORKFLOW_EXECUTION", "true")
    monkeypatch.setenv("N8N_WEBHOOK_URL", "http://example.test/webhook")
    with pytest.raises(HTTPException) as exc:
        integrations.dispatch_n8n_workflow(integrations.WorkflowDispatch(event="lead.qualified", payload={}), authorization="Bearer user-token")
    assert exc.value.status_code == 503


def test_n8n_dispatch_payload_does_not_forward_auth_tokens(monkeypatch):
    auth(monkeypatch)
    monkeypatch.setenv("N8N_ALLOW_WORKFLOW_EXECUTION", "true")
    monkeypatch.setenv("N8N_WEBHOOK_URL", "https://example.test/webhook")
    captured = {}

    class FakeResponse:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): return False

    def fake_urlopen(request, timeout):
        assert isinstance(request, Request)
        assert timeout == 10
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["headers"] = dict(request.header_items())
        return FakeResponse()

    monkeypatch.setattr(integrations, "urlopen", fake_urlopen)
    result = integrations.dispatch_n8n_workflow(integrations.WorkflowDispatch(event="lead.qualified", payload={"lead_id": "demo"}), authorization="Bearer user-token")
    assert result["status"] == "dispatched"
    assert captured["body"]["workspace_id"] == "business-1"
    assert "user-token" not in json.dumps(captured["body"])
    assert "Authorization" not in captured["headers"]
