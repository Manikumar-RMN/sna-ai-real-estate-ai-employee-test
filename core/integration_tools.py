"""Bridge approved integration actions into the Agent ToolRegistry."""
from typing import Iterable, Optional

from .integration_executor import IntegrationActionExecutor, IntegrationActionRegistry
from .integrations import IntegrationRegistry
from .tool_bundles import ToolBundle
from .tool_registry import Tool


def integration_tool_bundle(
    integrations: IntegrationRegistry,
    actions: IntegrationActionRegistry,
    *,
    allowed_permissions: Optional[Iterable[str]] = None,
    confirm_sensitive: bool = False,
) -> ToolBundle:
    """Create Agent-compatible tools for each registered integration action.

    The Agent's AgentConfig permissions should be configured consistently with
    allowed_permissions here. The integration executor applies its own second
    permission check when the handler is invoked.
    """
    executor = IntegrationActionExecutor(
        integrations,
        actions,
        allowed_permissions=allowed_permissions,
        confirm_sensitive=confirm_sensitive,
    )
    tools = []
    for integration in integrations.list_integrations():
        for action in actions.list_actions(integration.name):
            tool_name = f"integration__{integration.name}__{action.name}"

            def invoke(_integration=integration.name, _action=action.name, **arguments):
                result = executor.execute(_integration, _action, arguments)
                if result.ok:
                    return {"ok": True, "integration": result.integration,
                            "action": result.action, "output": result.output}
                return {"ok": False, "integration": result.integration,
                        "action": result.action, "error": result.error}

            tools.append(Tool(
                name=tool_name,
                description=f"{integration.name}: {action.description}",
                handler=invoke,
                schema=action.schema,
                permission=action.permission,
                category="integration",
                retryable=False,
            ))
    return ToolBundle(name="integrations", tools=tuple(tools))
