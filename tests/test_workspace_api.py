from fastapi import HTTPException
import pytest

from api import workspace


def test_workspace_requires_authenticated_session():
    with pytest.raises(HTTPException) as exc:
        workspace.get_workspace(authorization=None)
    assert exc.value.status_code == 401


def test_workspace_setup_creates_business_and_owner(monkeypatch):
    calls = []
    monkeypatch.setattr(workspace, "_authenticated_user", lambda authorization: ("token", {"id": "user-1", "email": "owner@example.test"}))
    monkeypatch.setattr(workspace, "_profile", lambda token, user_id: None)

    def fake_request(path, token=None, method="GET", payload=None, prefer=None):
        calls.append((path, method, payload, prefer))
        if path.startswith("/rest/v1/businesses"):
            return [{"id": "business-1", "name": "Example Co", "status": "active"}]
        if path == "/rest/v1/users":
            return [{"id": "profile-1"}]
        raise AssertionError(f"Unexpected request: {path}")

    monkeypatch.setattr(workspace, "_request", fake_request)
    result = workspace.create_workspace(workspace.WorkspaceCreate(business_name="Example Co", full_name="Owner Person"), authorization="Bearer token")
    assert result["status"] == "created"
    assert result["business"]["id"] == "business-1"
    assert calls[0][1] == "POST"
    assert calls[1][2]["auth_user_id"] == "user-1"
    assert calls[1][2]["role"] == "owner"


def test_workspace_prevents_duplicate_bootstrap(monkeypatch):
    monkeypatch.setattr(workspace, "_authenticated_user", lambda authorization: ("token", {"id": "user-1", "email": "owner@example.test"}))
    monkeypatch.setattr(workspace, "_profile", lambda token, user_id: {"business_id": "business-1"})
    with pytest.raises(HTTPException) as exc:
        workspace.create_workspace(workspace.WorkspaceCreate(business_name="Example Co", full_name="Owner Person"), authorization="Bearer token")
    assert exc.value.status_code == 409


def test_agent_creation_is_scoped_to_authenticated_business(monkeypatch):
    monkeypatch.setattr(workspace, "_authenticated_user", lambda authorization: ("token", {"id": "user-1", "email": "owner@example.test"}))
    monkeypatch.setattr(workspace, "_profile", lambda token, user_id: {"business_id": "business-1"})
    captured = {}

    def fake_request(path, token=None, method="GET", payload=None, prefer=None):
        captured.update({"path": path, "method": method, "payload": payload, "prefer": prefer})
        return [{"id": "agent-1", "business_id": "business-1", "name": "Enquiry Assistant", "description": "Handles enquiries", "system_prompt": "private prompt", "status": "active"}]

    monkeypatch.setattr(workspace, "_request", fake_request)
    result = workspace.create_agent(workspace.AgentCreate(name="Enquiry Assistant", description="Handles enquiries", system_prompt="Ask questions and hand off when unsure."), authorization="Bearer token")
    assert captured["payload"]["business_id"] == "business-1"
    assert result["id"] == "agent-1"
    assert "system_prompt" not in result


def test_agent_creation_requires_workspace(monkeypatch):
    monkeypatch.setattr(workspace, "_authenticated_user", lambda authorization: ("token", {"id": "user-1", "email": "owner@example.test"}))
    monkeypatch.setattr(workspace, "_profile", lambda token, user_id: None)
    with pytest.raises(HTTPException) as exc:
        workspace.create_agent(workspace.AgentCreate(name="Enquiry Assistant", system_prompt="Ask questions and hand off when unsure."), authorization="Bearer token")
    assert exc.value.status_code == 409
