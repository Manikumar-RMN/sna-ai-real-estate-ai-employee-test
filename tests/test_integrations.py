import pytest

from core.integrations import (
    FunctionIntegration,
    IntegrationDescriptor,
    IntegrationHealth,
    IntegrationRegistry,
)


def adapter(name, capabilities=("read",)):
    return FunctionIntegration(IntegrationDescriptor(name=name, capabilities=capabilities))


def test_register_and_discover_integrations():
    registry = IntegrationRegistry()
    registry.register(adapter("crm", ("contacts.read", "contacts.write")))
    registry.register(adapter("calendar", ("events.read",)))
    assert registry.get("crm") is not None
    assert [item.name for item in registry.list_integrations(capability="events.read")] == ["calendar"]


def test_register_many_is_atomic_for_duplicate_names():
    registry = IntegrationRegistry()
    registry.register(adapter("crm"))
    with pytest.raises(ValueError, match="already registered"):
        registry.register_many([adapter("calendar"), adapter("crm")])
    assert [item.name for item in registry.list_integrations()] == ["crm"]


def test_health_check_without_live_connection_is_explicit():
    registry = IntegrationRegistry()
    registry.register(adapter("mock"))
    result = registry.health_check("mock")
    assert result.ok is True
    assert "no live connectivity check" in result.message


def test_health_check_uses_callback():
    registry = IntegrationRegistry()
    integration = FunctionIntegration(
        IntegrationDescriptor(name="service"),
        check=lambda: IntegrationHealth(ok=False, message="unavailable"),
    )
    registry.register(integration)
    assert registry.health_check("service") == IntegrationHealth(ok=False, message="unavailable")


def test_unknown_health_check_fails_clearly():
    with pytest.raises(ValueError, match="not found"):
        IntegrationRegistry().health_check("missing")


def test_descriptor_rejects_blank_name_and_capability():
    with pytest.raises(ValueError):
        IntegrationDescriptor(name=" ")
    with pytest.raises(ValueError):
        IntegrationDescriptor(name="service", capabilities=("",))
