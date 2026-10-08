import json
from typing import Any

from .executor import ToolExecutor
from .models import ChatModel
from .state import AgentState
from .tool_registry import ToolRegistry

SYSTEM_PROMPT = """You are an agent running inside the SNA AI Agent Engine.
Use tools when they are needed to complete the task.
Do not invent tool results.
If a tool fails, inspect the error and decide whether to retry, use another tool, or explain the limitation.
Finish with a clear answer when the task is complete."""

class Agent:
    def __init__(self, model: ChatModel, registry: ToolRegistry, max_steps: int = 8, tool_timeout_seconds: float = 30.0) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be >= 1")
        self.model = model
        self.registry = registry
        self.max_steps = max_steps
        self.executor = ToolExecutor(tool_timeout_seconds)

    def run(self, task: str) -> str:
        state = AgentState(task=task, messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task},
        ])

        for step in range(self.max_steps):
            state.step = step + 1
            response = self.model.chat(state.messages, self.registry.schemas())

            if response.tool_calls:
                state.messages.append({
                    "role": "assistant",
                    "content": response.content,
                    "tool_calls": [{"id": c.id, "name": c.name, "arguments": c.arguments} for c in response.tool_calls],
                })
                for call in response.tool_calls:
                    result = self.executor.execute(call.name, call.arguments, self.registry.handlers())
                    state.log.append({
                        "step": state.step,
                        "tool": call.name,
                        "arguments": call.arguments,
                        "result": result,
                    })
                    state.messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(result, default=str),
                    })
                continue

            return response.content or ""

        return "Stopped: step limit reached. Partial progress is available in the run log."
