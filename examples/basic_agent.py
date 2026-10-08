from core.agent import Agent
from core.models import ModelResponse, ToolCall
from core.tool_registry import Tool, ToolRegistry

def add(a,b): return a+b
class DemoModel:
    def __init__(self): self.called=False
    def chat(self,messages,tools):
        if not self.called:
            self.called=True; return ModelResponse(tool_calls=[ToolCall("1","add",'{"a":2,"b":3}')])
        return ModelResponse(content="The answer is 5.")

registry=ToolRegistry(); registry.register(Tool("add","Add two numbers.",add,{"type":"object","properties":{"a":{"type":"number"},"b":{"type":"number"}},"required":["a","b"],"additionalProperties":False}))
print(Agent(DemoModel(),registry).run("What is 2 + 3?"))
