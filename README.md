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
