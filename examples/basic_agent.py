from core.agent import Agent
from core.models import ModelMessage, ToolCall
from core.tool_registry import Tool, ToolRegistry
from tools.examples import add, ADD_TOOL_SCHEMA

class FakeModel:
    def __init__(self):
        self.calls = 0

    def chat(self, messages, tools):
        self.calls += 1
        if self.calls == 1:
            return ModelMessage(
                role="assistant",
                tool_calls=[ToolCall(id="1", name="add", arguments='{"a": 2, "b": 3}')]
            )
        return ModelMessage(role="assistant", content="The answer is 5.")

registry = ToolRegistry()
registry.register(Tool("add", "Add two numbers.", add, ADD_TOOL_SCHEMA))

agent = Agent(FakeModel(), registry)
print(agent.run("What is 2 + 3?"))
