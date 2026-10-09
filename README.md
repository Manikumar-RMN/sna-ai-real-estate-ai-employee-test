# SNA AI Agent Engine

Core runtime for SNA AI's reusable, tool-using AI agents.

## Purpose

This repository is dedicated to the SNA AI Agent Engine. It is intentionally independent of any business vertical, UI, database, CRM, WhatsApp integration, or model provider.

## Current architecture

- Agent runtime
- Tool registry and schemas
- Reusable tool bundles
- Safe tool execution
- Agent state and conversation memory
- Permissions and guardrails
- Run logging / observability
- Model-provider adapter boundary
- Run persistence boundary
- Knowledge-provider boundary
- Resumable execution

## V1.6 — Reusable Tool System

V1.6 adds a reusable capability layer on top of the existing tool registry:

- ToolBundle packages related tools as a reusable capability set
- ToolSet defines a lightweight interface for custom tool providers
- ToolRegistry.register_many() registers bundles atomically
- Tool discovery can be filtered by category or permission
- Standard provider-neutral utility tools are available through standard_tool_bundle()
- Standard tools do not call external services and introduce no new runtime dependencies

Business-specific bundles can later provide CRM, calendar, communication, or other integrations without changing the agent runtime.

## Production integration boundary

The engine remains intentionally separate from business-specific AI employees, external integrations, authentication, tenant isolation, secrets management, deployment infrastructure, billing, and admin UI.

## V1.7 — AI Employee Runtime

V1.7 adds a vertical-neutral employee layer on top of the core Agent:

- `EmployeeDefinition` captures an employee's name, role, description, goals, instructions, and metadata.
- `AIEmployee` composes that definition with the existing model, tool registry, permissions, knowledge provider, and run store.
- Employee tasks return the same structured `AgentResult` and support resume, cancellation, and knowledge search.
- Employee identity and goals are incorporated into the system prompt; runtime permissions and policy limits remain controlled by `AgentConfig`.

Example:

```python
from core import AIEmployee, EmployeeDefinition, ToolRegistry
from core.models import ModelResponse

class MyModel:
    def chat(self, messages, tools):
        return ModelResponse(content="Task completed.")

employee = AIEmployee(
    EmployeeDefinition(
        name="Operations Assistant",
        role="Operations",
        goals=("Complete routine tasks accurately",),
        instructions="Be concise and report blockers clearly.",
    ),
    model=MyModel(),
    registry=ToolRegistry(),
)
result = employee.run_result("Prepare today's status summary")
print(result.status, result.output)
```

This layer is still integration-neutral: CRM, messaging, email, and calendar adapters belong in the integration layer.

## V1.8 — Integration Layer

V1.8 introduces provider-neutral integration contracts without coupling the Agent runtime to external vendors:

- `IntegrationDescriptor` declares an adapter's name, version, description, capabilities, and non-secret metadata.
- `IntegrationAdapter` defines the minimal adapter contract and health-check behavior.
- `IntegrationRegistry` supports single and atomic batch registration, lookup, capability discovery, and health checks.
- `FunctionIntegration` provides a small helper for local/mock adapters.
- No credentials are stored by this layer, and registering an adapter does not make network calls.

Example:

```python
from core.integrations import (
    FunctionIntegration,
    IntegrationDescriptor,
    IntegrationRegistry,
)

registry = IntegrationRegistry()
registry.register(FunctionIntegration(
    descriptor=IntegrationDescriptor(
        name="crm",
        capabilities=("contacts.read", "contacts.write"),
    )
))
print(registry.list_integrations(capability="contacts.read"))
```

Concrete CRM, messaging, email, and calendar connectors can implement this contract in separate modules. Keep credentials in server-side configuration and require explicit authorization for write or sensitive operations. A registered adapter's default health check only confirms local registration, not external connectivity.


## V1.9 — Permission-Checked Integration Actions

V1.9 adds a separate action execution boundary on top of the V1.8 integration registry:

- `IntegrationAction` explicitly allow-lists each operation, JSON Schema, and permission.
- `IntegrationActionRegistry` only attaches actions to integrations already registered.
- `IntegrationActionExecutor` validates arguments before invoking handlers and defaults to read-only permissions.
- Write actions require an explicit permission grant. Sensitive actions require both a grant and `confirm_sensitive=True`.
- Missing actions, denied permissions, and invalid arguments fail closed. Handler exception text is not returned to the caller, helping prevent accidental credential leakage.
- This is a local execution boundary, not a credentials vault, tenant authorization system, or live external connector. Production applications must enforce authenticated user/tenant scope and resolve secrets server-side.

Example:

```python
from core.integration_executor import (
    IntegrationAction, IntegrationActionExecutor, IntegrationActionRegistry,
)
from core.integrations import FunctionIntegration, IntegrationDescriptor, IntegrationRegistry

integrations = IntegrationRegistry()
integrations.register(FunctionIntegration(IntegrationDescriptor(name="crm")))
actions = IntegrationActionRegistry(integrations)
actions.register("crm", IntegrationAction(
    name="lookup_contact",
    description="Look up one contact",
    schema={
        "type": "object",
        "properties": {"contact_id": {"type": "string"}},
        "required": ["contact_id"],
        "additionalProperties": False,
    },
    handler=lambda contact_id: {"contact_id": contact_id},
    permission="read",
))
executor = IntegrationActionExecutor(integrations, actions)
result = executor.execute("crm", "lookup_contact", {"contact_id": "demo-123"})
print(result.ok, result.output)
```

No real CRM, WhatsApp, email, or calendar service is connected by these tests; the examples use local handlers only.


## V2.0 — Mock CRM and Agent Runtime Bridge

V2.0 demonstrates the integration path end to end using an ephemeral in-memory CRM. It does not connect to a real CRM or persist contact data.

- `MockCRM` provides local search, get, create, and update contact operations with sample records.
- `register_mock_crm` registers explicit actions and declared capabilities.
- `integration_tool_bundle` exposes registered integration actions as namespaced Agent tools, such as `integration__mock_crm__search_contacts`.
- The existing Agent tool executor and the integration action executor both enforce permissions. Keep their `allowed_permissions` and `confirm_sensitive` settings aligned.
- Read actions work with the default read-only policy. Create/update actions are denied unless write permission is explicitly granted.
- Integration write tools are non-retryable by default to avoid accidental duplicate writes.

Example setup:

```python
from core import (
    AgentConfig, IntegrationActionRegistry, IntegrationRegistry,
    MockCRM, ToolRegistry, integration_tool_bundle, register_mock_crm,
)

integrations = IntegrationRegistry()
actions = IntegrationActionRegistry(integrations)
crm = register_mock_crm(integrations, actions, MockCRM())
tools = ToolRegistry()
integration_tool_bundle(integrations, actions).register_into(tools)

# Supply your chosen model provider to Agent/AIEmployee.
# Default permissions remain read-only; enable writes deliberately.
```

This is a local development/test adapter only. It is not tenant-isolated production storage and does not implement a real CRM API, OAuth, credential management, audit persistence, or human approval UI.


## V2.1 — Secure HTTP Integration Foundation

V2.1 adds a provider-neutral HTTP foundation for future external integrations:

- `TenantScopedHttpJsonClient` uses a fixed, application-configured base URL and accepts only relative paths; model-generated full URLs are not accepted.
- HTTPS is required by default. Plain HTTP is available only when explicitly enabled for local development.
- A `SecretProvider` resolves bearer credentials by tenant, integration, and secret name. The included `InMemorySecretProvider` is for tests/local development only; production should use a managed secrets vault.
- Requests have bounded timeouts and response sizes, allowlisted HTTP methods, JSON payload handling, and sanitized errors.
- Redirects are rejected to avoid forwarding authorization headers to another origin.
- Tenant identity must come from the authenticated application layer, never from an LLM tool argument. This client is not a substitute for authentication, authorization, vendor-specific OAuth, or tenant-isolation testing.

No external service is configured or called by the tests. Before connecting a real provider, implement a production secret provider, add vendor-specific endpoint/action allow-lists, and verify the authenticated tenant boundary.


## V2.2 — n8n Webhook Adapter

V2.2 adds a first provider-specific adapter using the secure HTTP foundation:

- `N8nWebhookAdapter` posts a JSON event to one fixed webhook path configured by the application.
- The webhook URL/path and tenant identity are not model-controlled arguments. Instantiate/register the adapter within the authenticated tenant's application context.
- The action is explicitly marked `write`, so it is denied by the default read-only integration executor until write permission is deliberately enabled.
- The health check is local-only and does not accidentally trigger a workflow.
- Tests use a fake transport; they do not contact n8n or any external service.

Example (configure `client`, secret provider, tenant, and webhook path on the server first):

```python
from core import (
    IntegrationActionExecutor, IntegrationActionRegistry, IntegrationRegistry,
    N8nWebhookAdapter, register_n8n_webhook,
)

integrations = IntegrationRegistry()
actions = IntegrationActionRegistry(integrations)
adapter = N8nWebhookAdapter(
    client=client,  # TenantScopedHttpJsonClient configured server-side
    tenant_id=authenticated_tenant_id,
    webhook_path="webhook/your-configured-webhook-id",
)
register_n8n_webhook(integrations, actions, adapter)

# Triggering workflows is a write action; grant deliberately.
executor = IntegrationActionExecutor(
    integrations, actions, allowed_permissions={"read", "write"},
)
result = executor.execute("n8n_webhook", "trigger", {
    "event_name": "lead.created",
    "payload": {"lead_id": "demo-123"},
})
```

This is not yet a live n8n connection. Production use still requires a managed secret provider, tenant-authentication boundary, vendor-specific authentication/configuration, webhook-side verification, audit logging, and an explicit configured endpoint. Never commit webhook URLs containing secret tokens or credentials.
