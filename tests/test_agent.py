from core.agent import Agent
from core.models import ModelMessage, ToolCall
from core.tool_registry import Tool, ToolRegistry

class FakeModel:
    def __init__(self, calls):
        self.calls = calls
        self.index = 0

    def chat(self, messages, tools):
        value = self.calls[self.index]
        self.index += 1
        return value

def test_agent_runs_tool_then_returns():
    registry = ToolRegistry()
    registry.register(Tool(
        name="add",
        description="Add two numbers.",
        handler=lambda a, b: a + b,
        schema={"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]},
    ))
    model = FakeModel([
        ModelMessage("assistant", tool_calls=[ToolCall("1", "add", '{"a":2,"b":3}')]),
        ModelMessage("assistant", content="5"),
    ])
    assert Agent(model, registry).run("2 + 3") == "5"

def test_agent_stops_at_limit():
    class LoopModel:
        def chat(self, messages, tools):
            return ModelMessage("assistant", tool_calls=[ToolCall("x", "add", '{"a":1,"b":1}')])
    registry = ToolRegistry()
    registry.register(Tool("add", "Add.", lambda a,b:a+b, {"type":"object"}))
    result = Agent(LoopModel(), registry, max_steps=2).run("loop")
    assert "step limit" in result
