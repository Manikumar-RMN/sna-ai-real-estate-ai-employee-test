from core.agent import Agent
from core.models import ModelResponse, ToolCall
from core.tool_registry import Tool, ToolRegistry


class FakeModel:
    def __init__(self, responses):
        self.responses, self.i = responses, 0

    def chat(self, messages, tools):
        response = self.responses[self.i]
        self.i += 1
        return response


def registry():
    r = ToolRegistry()
    r.register(Tool(
        "add",
        "Add two numbers.",
        lambda a, b: a + b,
        {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
            "additionalProperties": False,
        },
    ))
    return r


def test_agent_runs_tool_then_returns():
    model = FakeModel([
        ModelResponse(tool_calls=[ToolCall("1", "add", '{"a":2,"b":3}')]),
        ModelResponse(content="5"),
    ])
    assert Agent(model, registry()).run("2 + 3") == "5"


def test_agent_stops_at_limit():
    class Loop:
        def chat(self, messages, tools):
            return ModelResponse(tool_calls=[ToolCall("x", "add", '{"a":1,"b":1}')])

    assert "step limit" in Agent(Loop(), registry(), max_steps=2).run("loop")


def test_empty_task_rejected():
    model = FakeModel([])
    try:
        Agent(model, registry()).run("  ")
    except ValueError as e:
        assert "empty" in str(e)
    else:
        assert False


def test_agent_can_execute_write_when_explicitly_allowed():
    r = registry()
    r.register(Tool(
        "save",
        "Save data.",
        lambda value: value,
        {
            "type": "object",
            "properties": {"value": {"type": "string"}},
            "required": ["value"],
        },
        "write",
    ))
    model = FakeModel([
        ModelResponse(tool_calls=[ToolCall("1", "save", '{"value":"ok"}')]),
        ModelResponse(content="saved"),
    ])
    assert Agent(
        model, r, allowed_permissions={"read", "write"}
    ).run("save it") == "saved"


def test_agent_result_has_run_id_and_events():
    model = FakeModel([ModelResponse(content="done")])
    result = Agent(model, registry()).run_result("finish")
    assert result.run_id
    assert result.status == "completed"
    assert result.output == "done"
    assert result.steps == 1
    assert result.events[0]["type"] == "run_started"
    assert result.events[-1]["type"] == "run_completed"


def test_agent_result_records_tool_events():
    model = FakeModel([
        ModelResponse(tool_calls=[ToolCall("1", "add", '{"a":2,"b":3}')]),
        ModelResponse(content="5"),
    ])
    result = Agent(model, registry()).run_result("2 + 3")
    event_types = [event["type"] for event in result.events]
    assert "tool_call_started" in event_types
    assert "tool_call_completed" in event_types
    assert result.status == "completed"


def test_agent_result_records_step_limit():
    class Loop:
        def chat(self, messages, tools):
            return ModelResponse(tool_calls=[ToolCall("x", "add", '{"a":1,"b":1}')])

    result = Agent(Loop(), registry(), max_steps=2).run_result("loop")
    assert result.status == "step_limit"
    assert result.events[-1]["type"] == "run_stopped"
