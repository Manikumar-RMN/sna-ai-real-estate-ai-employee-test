import json
from typing import Iterable, Optional

from .executor import ToolExecutor
from .models import AgentResult, ChatModel
from .state import AgentState
from .store import InMemoryRunStore, RunStore
from .tool_registry import ToolRegistry

SYSTEM_PROMPT = """You are an agent running inside the SNA AI Agent Engine.
Use tools when they are needed to complete the task.
Never invent tool results.
If a tool fails, inspect the error and decide whether to retry, use another tool, or explain the limitation.
Finish with a clear answer when the task is complete."""


class Agent:
    def __init__(
        self,
        model: ChatModel,
        registry: ToolRegistry,
        max_steps: int = 8,
        tool_timeout_seconds: float = 30.0,
        allowed_permissions: Optional[Iterable[str]] = None,
        confirm_sensitive: bool = False,
        run_store: Optional[RunStore] = None,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be >= 1")
        self.model = model
        self.registry = registry
        self.max_steps = max_steps
        self.run_store = run_store or InMemoryRunStore()
        self.executor = ToolExecutor(
            tool_timeout_seconds,
            allowed_permissions=allowed_permissions,
            confirm_sensitive=confirm_sensitive,
        )

    def run(self, task: str) -> str:
        return self.run_result(task).output

    def run_result(self, task: str) -> AgentResult:
        if not task.strip():
            raise ValueError("task cannot be empty")

        state = AgentState(
            task=task,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": task},
            ],
        )
        state.record("run_started", 0, task=task)
        self.run_store.save(state)
        return self._execute(state)

    def resume(self, run_id: str) -> str:
        return self.resume_result(run_id).output

    def resume_result(self, run_id: str) -> AgentResult:
        state = self.run_store.get(run_id)
        if state is None:
            raise ValueError(f"run not found: {run_id}")
        if state.status == "completed":
            raise ValueError(f"run already completed: {run_id}")
        if state.status == "running":
            raise ValueError(f"run is already active: {run_id}")

        state.status = "running"
        state.record("run_resumed", state.step)
        self.run_store.save(state)
        return self._execute(state)

    def _execute(self, state: AgentState) -> AgentResult:
        for _ in range(self.max_steps):
            state.step += 1
            state.record("model_step_started", state.step)
            self.run_store.save(state)

            response = self.model.chat(state.messages, self.registry.schemas())
            calls = response.tool_calls or []

            if not calls:
                state.output = response.content or ""
                state.status = "completed"
                state.record("run_completed", state.step, output=state.output)
                self.run_store.save(state)
                return self._result(state)

            state.messages.append({
                "role": "assistant",
                "content": response.content,
                "tool_calls": [
                    {"id": c.id, "name": c.name, "arguments": c.arguments}
                    for c in calls
                ],
            })
            self.run_store.save(state)

            for call in calls:
                tool = self.registry.get(call.name)
                state.record("tool_call_started", state.step, tool=call.name)

                result = (
                    {"error": f"Unknown tool: {call.name}"}
                    if tool is None
                    else self.executor.execute(tool, call.arguments)
                )

                state.log.append({
                    "step": state.step,
                    "tool": call.name,
                    "arguments": call.arguments,
                    "result": result,
                })
                state.record(
                    "tool_call_completed",
                    state.step,
                    tool=call.name,
                    result=result,
                )
                state.messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, default=str),
                })
                self.run_store.save(state)

        state.status = "step_limit"
        state.output = "Stopped: step limit reached. Partial progress is available in the run log."
        state.record("run_stopped", state.step, reason="step_limit")
        self.run_store.save(state)
        return self._result(state)

    @staticmethod
    def _result(state: AgentState) -> AgentResult:
        return AgentResult(
            run_id=state.run_id,
            status=state.status,
            output=state.output,
            steps=state.step,
            events=[{
                "type": e.type,
                "timestamp": e.timestamp,
                "step": e.step,
                "data": e.data,
            } for e in state.events],
        )
