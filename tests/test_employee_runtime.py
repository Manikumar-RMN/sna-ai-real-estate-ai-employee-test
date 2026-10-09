import pytest

from core.employee import AIEmployee, EmployeeDefinition
from core.models import ModelResponse
from core.tool_registry import ToolRegistry


class FakeModel:
    def __init__(self):
        self.messages = []

    def chat(self, messages, tools):
        self.messages.append(messages)
        return ModelResponse(content="completed")


def test_employee_runtime_includes_definition():
    model = FakeModel()
    employee = AIEmployee(
        EmployeeDefinition(
            name="Operations Assistant",
            role="Operations",
            description="Helps with routine work.",
            goals=("Complete tasks accurately", "Escalate uncertainty"),
            instructions="Be concise.",
        ),
        model,
        ToolRegistry(),
    )
    result = employee.run_result("prepare a status update")
    assert result.status == "completed"
    prompt = model.messages[0][0]["content"]
    assert "Operations Assistant" in prompt
    assert "Complete tasks accurately" in prompt
    assert "Be concise." in prompt


@pytest.mark.parametrize("name,role", [("", "Support"), ("Agent", "")])
def test_employee_requires_name_and_role(name, role):
    with pytest.raises(ValueError):
        EmployeeDefinition(name=name, role=role)
