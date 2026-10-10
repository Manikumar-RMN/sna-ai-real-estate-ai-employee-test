import pytest
from fastapi import HTTPException

from api import index


def test_data_endpoints_require_authentication():
    with pytest.raises(HTTPException) as exc:
        index.list_businesses(None)
    assert exc.value.status_code == 401

    with pytest.raises(HTTPException) as exc:
        index.list_agents(None)
    assert exc.value.status_code == 401


def test_business_data_is_limited_to_authenticated_workspace(monkeypatch):
    monkeypatch.setattr(index, "_authenticated_user", lambda authorization: ("token", {"id": "user-1"}))
    monkeypatch.setattr(index, "_profile", lambda token, user_id: {"business_id": "workspace-123"})
    calls = []

    def fake_request(path, token=None, **kwargs):
        calls.append((path, token))
        return [{"id": "workspace-123", "name": "Test workspace", "status": "active"}]

    monkeypatch.setattr(index, "_request", fake_request)
    result = index.list_businesses("Bearer test-token")

    assert result["count"] == 1
    assert calls == [("/rest/v1/businesses?select=id,name,status,created_at&id=eq.workspace-123&limit=1", "token")]


def test_agent_data_is_limited_to_authenticated_workspace(monkeypatch):
    monkeypatch.setattr(index, "_authenticated_user", lambda authorization: ("token", {"id": "user-1"}))
    monkeypatch.setattr(index, "_profile", lambda token, user_id: {"business_id": "workspace-123"})
    calls = []

    def fake_request(path, token=None, **kwargs):
        calls.append((path, token))
        return [{"id": "agent-1", "name": "Test agent", "status": "active"}]

    monkeypatch.setattr(index, "_request", fake_request)
    result = index.list_agents("Bearer test-token")

    assert result["count"] == 1
    assert "business_id=eq.workspace-123" in calls[0][0]
    assert "select=*" not in calls[0][0]
    assert calls[0][1] == "token"
