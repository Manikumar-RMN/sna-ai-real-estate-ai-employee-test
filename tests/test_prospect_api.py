from fastapi import HTTPException
import pytest

from api import workspace


def test_prospect_creation_binds_authenticated_business_and_validates_stage(monkeypatch):
    monkeypatch.setattr(workspace, "_authenticated_user", lambda authorization: ("token", {"id": "user-1", "email": "owner@example.test"}))
    monkeypatch.setattr(workspace, "_profile", lambda token, user_id: {"business_id": "business-1"})
    captured = {}

    def fake_request(path, token=None, method="GET", payload=None, prefer=None):
        captured.update({"path": path, "method": method, "payload": payload})
        return [{"id": "prospect-1", "business_id": "business-1", "name": "Example Coaching", "segment": "coaching", "stage": "researched", "score": 70}]

    monkeypatch.setattr(workspace, "_request", fake_request)
    body = workspace.ProspectCreate(name="Example Coaching", segment="coaching", city="Karaikudi", score=70)
    result = workspace.create_prospect(body, authorization="Bearer token")
    assert captured["payload"]["business_id"] == "business-1"
    assert captured["payload"]["stage"] == "researched"
    assert result["id"] == "prospect-1"


def test_prospect_creation_requires_workspace(monkeypatch):
    monkeypatch.setattr(workspace, "_authenticated_user", lambda authorization: ("token", {"id": "user-1", "email": "owner@example.test"}))
    monkeypatch.setattr(workspace, "_profile", lambda token, user_id: None)
    with pytest.raises(HTTPException) as exc:
        workspace.create_prospect(workspace.ProspectCreate(name="Example Coaching"), authorization="Bearer token")
    assert exc.value.status_code == 409


def test_prospect_stage_validation_rejects_unknown_stage():
    with pytest.raises(ValueError):
        workspace.ProspectStageUpdate(stage="send_spam")
