"""Permission-checked execution for registered integration actions.

This module performs no network calls itself. Action handlers belong to
provider adapters and must resolve credentials from server-side configuration.
"""
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional

from jsonschema import Draft202012Validator, ValidationError

from .tool_registry import PERMISSIONS
from .integrations import IntegrationRegistry


@dataclass(frozen=True)
class IntegrationAction:
    """One explicitly allow-listed operation exposed by an integration."""

    name: str
    description: str
    handler: Callable[..., Any]
    schema: Dict[str, Any]
    permission: str = "read"
    capability: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("integration action name cannot be empty")
        if not isinstance(self.description, str):
            raise ValueError("integration action description must be a string")
        if not callable(self.handler):
            raise ValueError("integration action handler must be callable")
        if self.permission not in PERMISSIONS:
            raise ValueError(f"invalid integration action permission: {self.permission}")
        if not isinstance(self.schema, dict):
            raise ValueError("integration action schema must be a dictionary")
        Draft202012Validator.check_schema(self.schema)
        if self.capability is not None and (
            not isinstance(self.capability, str) or not self.capability.strip()
        ):
            raise ValueError("integration action capability cannot be blank")


@dataclass(frozen=True)
class IntegrationActionResult:
    ok: bool
    integration: str
    action: str
    output: Any = None
    error: Optional[str] = None


class IntegrationActionRegistry:
    """Stores explicit action allow-lists for already registered integrations."""

    def __init__(self, integrations: IntegrationRegistry) -> None:
        self.integrations = integrations
        self._actions: Dict[str, Dict[str, IntegrationAction]] = {}

    def register(self, integration_name: str, action: IntegrationAction) -> None:
        if self.integrations.get(integration_name) is None:
            raise ValueError(f"integration not found: {integration_name}")
        actions = self._actions.setdefault(integration_name, {})
        if action.name in actions:
            raise ValueError(
                f"integration action already registered: {integration_name}.{action.name}"
            )
        actions[action.name] = action

    def get(self, integration_name: str, action_name: str) -> Optional[IntegrationAction]:
        return self._actions.get(integration_name, {}).get(action_name)

    def list_actions(self, integration_name: str) -> List[IntegrationAction]:
        if self.integrations.get(integration_name) is None:
            raise ValueError(f"integration not found: {integration_name}")
        return list(self._actions.get(integration_name, {}).values())


class IntegrationActionExecutor:
    """Executes only allow-listed actions after permission and schema checks.

    Defaults to read-only. Write actions need an explicit write permission grant;
    sensitive actions additionally require confirm_sensitive=True. Denials and
    handler exceptions do not expose argument values, credentials, or exception
    text to callers.
    """

    def __init__(
        self,
        integrations: IntegrationRegistry,
        actions: IntegrationActionRegistry,
        *,
        allowed_permissions: Optional[Iterable[str]] = None,
        confirm_sensitive: bool = False,
    ) -> None:
        self.integrations = integrations
        self.actions = actions
        self.allowed_permissions = set({"read"} if allowed_permissions is None else allowed_permissions)
        invalid = self.allowed_permissions.difference(PERMISSIONS)
        if invalid:
            raise ValueError(f"invalid allowed permissions: {', '.join(sorted(invalid))}")
        self.confirm_sensitive = confirm_sensitive

    def execute(
        self,
        integration_name: str,
        action_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> IntegrationActionResult:
        action = self.actions.get(integration_name, action_name)
        if action is None:
            return IntegrationActionResult(
                False, integration_name, action_name, error="Integration action not found."
            )

        if action.permission not in self.allowed_permissions:
            return IntegrationActionResult(
                False, integration_name, action_name,
                error=f"Permission denied for {action.permission} action.",
            )
        if action.permission == "sensitive" and not self.confirm_sensitive:
            return IntegrationActionResult(
                False, integration_name, action_name,
                error="Explicit confirmation is required for this sensitive action.",
            )

        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            return IntegrationActionResult(
                False, integration_name, action_name,
                error="Action arguments must be a JSON object.",
            )
        try:
            Draft202012Validator(action.schema).validate(arguments)
        except ValidationError:
            return IntegrationActionResult(
                False, integration_name, action_name,
                error="Invalid action arguments; check the action schema.",
            )

        try:
            output = action.handler(**arguments)
        except Exception:
            # Do not return raw exception text: adapters may accidentally include secrets.
            return IntegrationActionResult(
                False, integration_name, action_name,
                error="Integration action failed; inspect server-side diagnostics.",
            )
        return IntegrationActionResult(True, integration_name, action_name, output=output)
