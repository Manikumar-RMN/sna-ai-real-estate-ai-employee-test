import json

from core import (
    AIEmployee,
    EmployeeDefinition,
    IntegrationActionRegistry,
    IntegrationRegistry,
    MockCRM,
    ToolRegistry,
    integration_tool_bundle,
    register_mock_crm,
)
from core.config import AgentConfig
from core.models import ModelResponse, ToolCall


class SearchThenSummarizeModel:
    def chat(self, messages, tools):
        if not any(message.get("role") == "tool" for message in messages):
            assert any(tool["name"] == "integration__mock_crm__search_contacts" for tool in tools)
            return ModelResponse(tool_calls=[ToolCall(
                id="test-search-1",
                name="integration__mock_crm__search_contacts",
                arguments=json.dumps({"query": "Asha"}),
            )])
        tool_result = json.loads(next(
            message["content"] for message in reversed(messages)
            if message.get("role") == "tool"
        ))
        assert tool_result["ok"] is True
        return ModelResponse(content="Found Asha Kumar; internal handoff prepared, no contact sent.")


def test_employee_uses_mock_crm_read_tool_without_write_permission():
    integrations = IntegrationRegistry()
    actions = IntegrationActionRegistry(integrations)
    crm = register_mock_crm(integrations, actions, MockCRM())
    tools = ToolRegistry()
    integration_tool_bundle(integrations, actions).register_into(tools)
    employee = AIEmployee(
        EmployeeDefinition(
            name="Lead Qualification Employee",
            role="Inbound Lead Qualification",
            goals=("Summarize inbound leads",),
            instructions="Do not send messages.",
        ),
        SearchThenSummarizeModel(),
        tools,
        config=AgentConfig(),
    )

    result = employee.run_result("Find Asha and prepare an internal handoff.")

    assert result.status == "completed"
    assert "Asha Kumar" in result.output
    assert "no contact sent" in result.output
    assert crm.get_contact("c-100")["name"] == "Asha Kumar"
    assert employee.agent.config.allowed_permissions == {"read"}
