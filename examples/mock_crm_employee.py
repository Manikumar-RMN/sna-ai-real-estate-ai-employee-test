"""Offline end-to-end AI employee + mock CRM demo.

Uses a deterministic model stub and an in-memory CRM. No API key, network
request, external CRM account, or paid model usage is required.
"""
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


class DemoModel:
    """Small deterministic stand-in that exercises the real tool-call bridge."""

    def chat(self, messages, tools):
        tool_name = "integration__mock_crm__search_contacts"
        if not any(message.get("role") == "tool" for message in messages):
            return ModelResponse(tool_calls=[ToolCall(
                id="demo-search-1",
                name=tool_name,
                arguments=json.dumps({"query": "Asha"}),
            )])

        tool_result = next(message["content"] for message in reversed(messages)
                           if message.get("role") == "tool")
        parsed = json.loads(tool_result)
        contacts = parsed.get("output", {}).get("contacts", [])
        if contacts:
            names = ", ".join(contact["name"] for contact in contacts)
            return ModelResponse(content=(
                f"CRM lookup completed. Matching contact(s): {names}. "
                "This is a demo summary only; no message was sent and no record was changed."
            ))
        return ModelResponse(content=(
            "No matching contact was found. No message was sent and no record was changed."
        ))


def main():
    integrations = IntegrationRegistry()
    actions = IntegrationActionRegistry(integrations)
    register_mock_crm(integrations, actions, MockCRM())
    tools = ToolRegistry()
    integration_tool_bundle(integrations, actions).register_into(tools)

    employee = AIEmployee(
        EmployeeDefinition(
            name="Lead Qualification Employee",
            role="Inbound Lead Qualification",
            goals=("Use approved CRM read tools accurately", "Never contact a prospect without consent"),
            instructions="Summarize the result. Do not claim any write or message was performed.",
        ),
        DemoModel(),
        tools,
        config=AgentConfig(),  # read-only by default
    )
    result = employee.run_result(
        "Find Asha in the CRM and prepare a brief internal lead handoff. Do not contact anyone."
    )
    print("Status:", result.status)
    print("Output:", result.output)
    print("Run ID:", result.run_id)


if __name__ == "__main__":
    main()
