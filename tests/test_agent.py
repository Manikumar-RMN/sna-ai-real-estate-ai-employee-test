from core.agent import Agent
from core.config import AgentConfig, RuntimeContext
from core.models import ModelResponse, ToolCall
from core.store import InMemoryRunStore
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

    assert "step limit" in Agent(Loop(), registry(), AgentConfig(max_steps=2)).run("loop")


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
        model, r, AgentConfig(allowed_permissions={"read", "write"})
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

    result = Agent(Loop(), registry(), AgentConfig(max_steps=2)).run_result("loop")
    assert result.status == "step_limit"


def test_run_is_persisted_and_can_be_resumed():
    store = InMemoryRunStore()
    model = FakeModel([
        ModelResponse(tool_calls=[ToolCall("1", "add", '{"a":2,"b":3}')]),
        ModelResponse(content="done"),
    ])
    agent = Agent(model, registry(), AgentConfig(max_steps=1), run_store=store)

    first = agent.run_result("calculate")
    assert first.status == "step_limit"

    saved = store.get(first.run_id)
    assert saved is not None
    assert saved.status == "step_limit"
    assert saved.step == 1
    assert len(saved.log) == 1

    resumed = agent.resume_result(first.run_id)
    assert resumed.run_id == first.run_id
    assert resumed.status == "completed"
    assert resumed.output == "done"
    assert resumed.steps == 2
    assert any(e["type"] == "run_resumed" for e in resumed.events)


def test_missing_run_cannot_resume():
    agent = Agent(FakeModel([]), registry())
    try:
        agent.resume_result("missing")
    except ValueError as e:
        assert "run not found" in str(e)
    else:
        assert False


def test_completed_run_cannot_resume():
    store = InMemoryRunStore()
    agent = Agent(FakeModel([ModelResponse(content="done")]), registry(), run_store=store)
    result = agent.run_result("finish")

    try:
        agent.resume_result(result.run_id)
    except ValueError as e:
        assert "already completed" in str(e)
    else:
        assert False


def test_runtime_context_is_injected_into_system_message():
    model = FakeModel([ModelResponse(content="done")])
    context = RuntimeContext(business_id="biz-1", channel="whatsapp")
    agent = Agent(model, registry())
    result = agent.run_result("hello", context)
    state = agent.run_store.get(result.run_id)
    assert state is not None
    assert "biz-1" in state.messages[0]["content"]
    assert "whatsapp" in state.messages[0]["content"]
