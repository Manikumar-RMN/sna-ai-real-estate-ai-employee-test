import pytest

from core.integration_executor import (
    IntegrationAction,
    IntegrationActionExecutor,
    IntegrationActionRegistry,
)
from core.integrations import FunctionIntegration, IntegrationDescriptor, IntegrationRegistry


def setup():
    integrations = IntegrationRegistry()
    integrations.register(FunctionIntegration(IntegrationDescriptor(
        name="crm", capabilities=("contacts.read", "contacts.write")
    )))
    actions = IntegrationActionRegistry(integrations)
    return integrations, actions


def action(name="lookup", permission="read", handler=None, schema=None):
    return IntegrationAction(
        name=name,
        description="Test action",
        handler=handler or (lambda **kwargs: {"received": kwargs}),
        schema=schema or {
            "type": "object",
            "properties": {"contact_id": {"type": "string"}},
            "required": ["contact_id"],
            "additionalProperties": False,
        },
        permission=permission,
    )


def test_read_action_executes_after_schema_validation():
    integrations, actions = setup()
    actions.register("crm", action())
    executor = IntegrationActionExecutor(integrations, actions)
    result = executor.execute("crm", "lookup", {"contact_id": "c-123"})
    assert result.ok
    assert result.output == {"received": {"contact_id": "c-123"}}


def test_write_action_is_denied_by_default_and_handler_not_called():
    integrations, actions = setup()
    called = []
    actions.register("crm", action(
        name="update", permission="write",
        handler=lambda **kwargs: called.append(kwargs),
    ))
    result = IntegrationActionExecutor(integrations, actions).execute(
        "crm", "update", {"contact_id": "c-123"}
    )
    assert not result.ok
    assert "Permission denied" in result.error
    assert called == []


def test_write_action_requires_explicit_permission_grant():
    integrations, actions = setup()
    actions.register("crm", action(name="update", permission="write"))
    executor = IntegrationActionExecutor(
        integrations, actions, allowed_permissions={"read", "write"}
    )
    assert executor.execute("crm", "update", {"contact_id": "c-123"}).ok


def test_sensitive_action_requires_confirmation_even_when_allowed():
    integrations, actions = setup()
    actions.register("crm", action(name="export", permission="sensitive"))
    executor = IntegrationActionExecutor(
        integrations, actions, allowed_permissions={"sensitive"}
    )
    denied = executor.execute("crm", "export", {"contact_id": "c-123"})
    assert not denied.ok
    assert "confirmation" in denied.error.lower()

    confirmed = IntegrationActionExecutor(
        integrations, actions, allowed_permissions={"sensitive"}, confirm_sensitive=True
    )
    assert confirmed.execute("crm", "export", {"contact_id": "c-123"}).ok


def test_invalid_arguments_do_not_call_handler():
    integrations, actions = setup()
    called = []
    actions.register("crm", action(handler=lambda **kwargs: called.append(kwargs)))
    result = IntegrationActionExecutor(integrations, actions).execute(
        "crm", "lookup", {"contact_id": 123, "unexpected": True}
    )
    assert not result.ok
    assert "Invalid action arguments" in result.error
    assert called == []


def test_unknown_action_fails_closed():
    integrations, actions = setup()
    result = IntegrationActionExecutor(integrations, actions).execute(
        "crm", "delete_everything", {}
    )
    assert not result.ok
    assert result.error == "Integration action not found."


def test_action_registration_requires_registered_integration():
    integrations = IntegrationRegistry()
    actions = IntegrationActionRegistry(integrations)
    with pytest.raises(ValueError, match="integration not found"):
        actions.register("missing", action())


def test_handler_exception_does_not_leak_exception_text():
    integrations, actions = setup()

    def broken_handler(**kwargs):
        raise RuntimeError("token=very-secret-value")

    actions.register("crm", action(handler=broken_handler))
    result = IntegrationActionExecutor(integrations, actions).execute(
        "crm", "lookup", {"contact_id": "c-123"}
    )
    assert not result.ok
    assert "very-secret-value" not in result.error
    assert "server-side diagnostics" in result.error


def test_empty_permission_set_denies_everything():
    integrations, actions = setup()
    actions.register("crm", action())
    executor = IntegrationActionExecutor(integrations, actions, allowed_permissions=set())
    assert not executor.execute("crm", "lookup", {"contact_id": "c-123"}).ok



def test_action_capability_must_be_declared_by_integration():
    integrations, actions = setup()
    invalid = action()
    invalid = IntegrationAction(
        name=invalid.name,
        description=invalid.description,
        handler=invalid.handler,
        schema=invalid.schema,
        permission=invalid.permission,
        capability="contacts.delete",
    )
    with pytest.raises(ValueError, match="does not declare capability"):
        actions.register("crm", invalid)
