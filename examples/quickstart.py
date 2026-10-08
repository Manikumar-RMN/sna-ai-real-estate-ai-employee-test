from core import Agent, AgentConfig, RuntimeContext, ModelResponse, Tool, ToolRegistry


class DemoModel:
    def chat(self, messages, tools):
        return ModelResponse(content="Engine is ready.")


registry = ToolRegistry()
registry.register(Tool(
    name="get_status",
    description="Return the current engine status.",
    handler=lambda: {"status": "ok"},
    schema={"type": "object"},
    permission="read",
    category="system",
))

agent = Agent(
    DemoModel(),
    registry,
    AgentConfig(max_steps=4),
)

result = agent.run_result(
    "Check the engine.",
    RuntimeContext(channel="demo", metadata={"environment": "local"}),
)

print(result.status)
print(result.output)
