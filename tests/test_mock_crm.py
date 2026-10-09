import json

from core.agent import Agent
from core.config import AgentConfig
from core.integration_executor import IntegrationActionRegistry
from core.integration_tools import integration_tool_bundle
from core.integrations import IntegrationRegistry
from core.mock_crm import MockCRM, register_mock_crm
from core.models import ModelResponse, ToolCall
from core.tool_registry import ToolRegistry


class OneToolModel:
    def __init__(self, tool_name, arguments):
        self.tool_name = tool_name
        self.arguments = json.dumps(arguments)
        self.calls = 0
        self.messages = []

    def chat(self, messages, tools):
        self.messages.append(messages)
        self.calls += 1
        if self.calls == 1:
            assert any(tool["name"] == self.tool_name for tool in tools)
            return ModelResponse(tool_calls=[
                ToolCall(id="call-1", name=self.tool_name, arguments=self.arguments)
            ])
        return ModelResponse(content="CRM lookup completed.")


def setup_engine(*, permissions=None, confirm_sensitive=False, crm=None, model=None):
    integrations = IntegrationRegistry()
    actions = IntegrationActionRegistry(integrations)
    crm = register_mock_crm(integrations, actions, crm)
    registry = ToolRegistry()
    bundle = integration_tool_bundle(
        integrations, actions,
        allowed_permissions=permissions,
        confirm_sensitive=confirm_sensitive,
    )
    bundle.register_into(registry)
    config = AgentConfig(
        allowed_permissions={"read"} if permissions is None else set(permissions),
        confirm_sensitive=confirm_sensitive,
    )
    return Agent(model or OneToolModel(
        "integration__mock_crm__search_contacts", {"query": "Asha"}
    ), registry, config), crm, registry


def test_mock_crm_search_action_is_available_to_agent():
    model = OneToolModel("integration__mock_crm__search_contacts", {"query": "Asha"})
    agent, crm, registry = setup_engine(model=model)
    result = agent.run_result("Find Asha in the CRM")
    assert result.status == "completed"
    assert any(tool.name == "integration__mock_crm__search_contacts" for tool in registry.list_tools())
    assert result.events


def test_mock_crm_search_returns_seed_contact():
    integrations = IntegrationRegistry()
    actions = IntegrationActionRegistry(integrations)
    crm = register_mock_crm(integrations, actions)
    action = actions.get("mock_crm", "search_contacts")
    result = action.handler(query="Asha")
    assert result["count"] == 1
    assert result["contacts"][0]["email"] == "asha@example.test"


def test_mock_crm_create_contact_is_denied_under_read_only_defaults():
    model = OneToolModel(
        "integration__mock_crm__create_contact",
        {"name": "Demo User", "email": "demo@example.test"},
    )
    agent, crm, _ = setup_engine(model=model)
    result = agent.run_result("Create a demo contact")
    assert result.status == "completed"
    assert crm.search_contacts("Demo User")["count"] == 0
    tool_results = [entry["result"] for entry in agent.run_store.get(result.run_id).log]
    assert tool_results
    assert tool_results[0]["error"].startswith("Permission denied")


def test_mock_crm_create_contact_works_when_write_is_explicitly_granted():
    model = OneToolModel(
        "integration__mock_crm__create_contact",
        {"name": "Demo User", "email": "demo@example.test"},
    )
    agent, crm, _ = setup_engine(permissions={"read", "write"}, model=model)
    result = agent.run_result("Create a demo contact")
    assert result.status == "completed"
    assert crm.search_contacts("Demo User")["count"] == 1


def test_mock_crm_write_tool_has_no_automatic_retry():
    agent, _, registry = setup_engine()
    tool = registry.get("integration__mock_crm__create_contact")
    assert tool.retryable is False
