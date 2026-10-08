from core.employee import AIEmployee, EmployeeDefinition
from core.models import ModelResponse
from core.tool_registry import ToolRegistry

class FakeModel:
    def __init__(self):
        self.messages = []
    def chat(self, messages, tools):
        self.messages.append(messages)
        return ModelResponse(content="completed")

def test_employee_runtime():
    model = FakeModel()
    employee = AIEmployee(
        EmployeeDefinition(
            name="Operations Assistant",
            role="Operations",
            goals=("Complete tasks accurately",),
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
