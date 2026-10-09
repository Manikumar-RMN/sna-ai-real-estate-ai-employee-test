"""n8n webhook adapter built on the secure HTTP integration client.

Configure one fixed webhook endpoint per adapter instance. The endpoint URL,
tenant identity, and credentials are application configuration and must never
come from model-generated tool arguments. No live request is made at setup time.
"""
from typing import Any, Dict

from .integration_executor import IntegrationAction, IntegrationActionRegistry
from .integrations import IntegrationDescriptor, IntegrationHealth, IntegrationRegistry
from .secure_http import TenantScopedHttpJsonClient


class N8nWebhookAdapter:
    """Trigger a configured n8n webhook for the authenticated tenant.

    Instantiate this adapter inside the authenticated tenant's application
    context. Do not register one instance globally and let an LLM choose tenant_id.
    """

    def __init__(
        self,
        *,
        client: TenantScopedHttpJsonClient,
        tenant_id: str,
        webhook_path: str,
    ) -> None:
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise ValueError("tenant_id must come from authenticated application context")
        TenantScopedHttpJsonClient.validate_relative_path(webhook_path)
        self.client = client
        self.tenant_id = tenant_id
        self.webhook_path = webhook_path
        self._descriptor = IntegrationDescriptor(
            name="n8n_webhook",
            version="1.0",
            description="Trigger one preconfigured n8n webhook",
            capabilities=("workflows.trigger",),
            metadata={"transport": "https-json"},
        )

    @property
    def descriptor(self) -> IntegrationDescriptor:
        return self._descriptor

    def health_check(self) -> IntegrationHealth:
        return IntegrationHealth(
            ok=True,
            message="Webhook adapter configured locally; no live connectivity check was performed.",
        )

    def trigger(self, *, event_name: str, payload: Dict[str, Any]) -> Any:
        if not isinstance(event_name, str) or not event_name.strip():
            raise ValueError("event_name must be a non-empty string")
        if len(event_name) > 120:
            raise ValueError("event_name is too long")
        if not isinstance(payload, dict):
            raise ValueError("payload must be a JSON object")
        return self.client.request(
            tenant_id=self.tenant_id,
            method="POST",
            path=self.webhook_path,
            payload={"event": event_name, "data": payload},
        )


def register_n8n_webhook(
    integrations: IntegrationRegistry,
    actions: IntegrationActionRegistry,
    adapter: N8nWebhookAdapter,
) -> N8nWebhookAdapter:
    """Register one configured adapter and its explicitly allow-listed trigger action."""
    integrations.register(adapter)
    actions.register(
        "n8n_webhook",
        IntegrationAction(
            name="trigger",
            description="Send an event and JSON payload to the preconfigured n8n webhook",
            schema={
                "type": "object",
                "properties": {
                    "event_name": {"type": "string", "minLength": 1, "maxLength": 120},
                    "payload": {"type": "object"},
                },
                "required": ["event_name", "payload"],
                "additionalProperties": False,
            },
            handler=adapter.trigger,
            permission="write",
            capability="workflows.trigger",
        ),
    )
    return adapter
