from core.agent import Agent
from core.models import ModelResponse, ToolCall
from core.tool_registry import Tool, ToolRegistry

class FakeModel:
    def __init__(self, responses): self.responses, self.i = responses, 0
    def chat(self, messages, tools):
        response = self.responses[self.i]; self.i += 1; return response

def registry():
    r=ToolRegistry(); r.register(Tool("add","Add two numbers.",lambda a,b:a+b,{"type":"object","properties":{"a":{"type":"number"},"b":{"type":"number"}},"required":["a","b"],"additionalProperties":False})); return r

def test_agent_runs_tool_then_returns():
    model=FakeModel([ModelResponse(tool_calls=[ToolCall("1","add",'{"a":2,"b":3}')]),ModelResponse(content="5")])
    assert Agent(model,registry()).run("2 + 3") == "5"

def test_agent_stops_at_limit():
    class Loop:
        def chat(self,messages,tools): return ModelResponse(tool_calls=[ToolCall("x","add",'{"a":1,"b":1}')])
    assert "step limit" in Agent(Loop(),registry(),max_steps=2).run("loop")

def test_empty_task_rejected():
    model=FakeModel([])
    try: Agent(model,registry()).run("  ")
    except ValueError as e: assert "empty" in str(e)
    else: assert False
