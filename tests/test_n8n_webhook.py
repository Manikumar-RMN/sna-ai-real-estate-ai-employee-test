import json

import pytest

from core.integration_executor import IntegrationActionExecutor, IntegrationActionRegistry
from core.integrations import IntegrationRegistry
from core.n8n_webhook import N8nWebhookAdapter, register_n8n_webhook
from core.secure_http import HttpResponse, InMemorySecretProvider, TenantScopedHttpJsonClient


class FakeTransport:
    def __init__(self, response=None):
        self.response = response or HttpResponse(200, b'{"accepted": true}')
        self.calls = []

    def send(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def make_adapter(tenant_id="tenant-a"):
    transport = FakeTransport()
    secrets = InMemorySecretProvider({
        (tenant_id, "n8n_webhook", "access_token"): "tenant-token",
    })
    client = TenantScopedHttpJsonClient(
        integration_name="n8n_webhook",
        base_url="https://n8n.example.test",
        secret_provider=secrets,
        transport=transport,
    )
    adapter = N8nWebhookAdapter(
        client=client, tenant_id=tenant_id, webhook_path="webhook/demo-hook",
    )
    return adapter, transport


def test_n8n_adapter_posts_event_to_only_configured_webhook():
    adapter, transport = make_adapter()
    result = adapter.trigger(event_name="lead.created", payload={"lead_id": "lead-123"})
    assert result == {"accepted": True}
    call = transport.calls[0]
    assert call["method"] == "POST"
    assert call["url"] == "https://n8n.example.test/webhook/demo-hook"
    assert call["headers"]["Authorization"] == "Bearer tenant-token"
    assert json.loads(call["body"]) == {
        "event": "lead.created", "data": {"lead_id": "lead-123"},
    }


def test_adapter_rejects_unsafe_webhook_path():
    adapter, _ = make_adapter()
    with pytest.raises(ValueError):
        N8nWebhookAdapter(
            client=adapter.client, tenant_id="tenant-a",
            webhook_path="https://evil.example/steal",
        )


def test_registration_exposes_write_action_and_executor_denies_by_default():
    adapter, transport = make_adapter()
    integrations = IntegrationRegistry()
    actions = IntegrationActionRegistry(integrations)
    register_n8n_webhook(integrations, actions, adapter)

    denied = IntegrationActionExecutor(integrations, actions).execute(
        "n8n_webhook", "trigger",
        {"event_name": "lead.created", "payload": {"lead_id": "lead-123"}},
    )
    assert not denied.ok
    assert "Permission denied" in denied.error
    assert transport.calls == []

    allowed = IntegrationActionExecutor(
        integrations, actions, allowed_permissions={"read", "write"},
    ).execute(
        "n8n_webhook", "trigger",
        {"event_name": "lead.created", "payload": {"lead_id": "lead-123"}},
    )
    assert allowed.ok
    assert transport.calls


def test_action_schema_rejects_extra_fields():
    adapter, transport = make_adapter()
    integrations = IntegrationRegistry()
    actions = IntegrationActionRegistry(integrations)
    register_n8n_webhook(integrations, actions, adapter)
    result = IntegrationActionExecutor(
        integrations, actions, allowed_permissions={"read", "write"},
    ).execute(
        "n8n_webhook", "trigger",
        {"event_name": "test", "payload": {}, "url": "https://evil.example"},
    )
    assert not result.ok
    assert "Invalid action arguments" in result.error
    assert transport.calls == []


def test_health_check_does_not_trigger_webhook():
    adapter, transport = make_adapter()
    health = adapter.health_check()
    assert health.ok
    assert "no live connectivity" in health.message
    assert transport.calls == []
