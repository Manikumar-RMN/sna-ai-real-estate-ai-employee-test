import json
from typing import Optional
from .config import AgentConfig, RuntimeContext, build_system_prompt
from .executor import ToolExecutor
from .knowledge import KnowledgeProvider
from .knowledge_runtime import NullKnowledgeProvider
from .models import AgentResult, ChatModel
from .state import AgentState
from .store import InMemoryRunStore, RunStore
from .tool_registry import ToolRegistry

class Agent:
    def __init__(self, model: ChatModel, registry: ToolRegistry, config: Optional[AgentConfig] = None, run_store: Optional[RunStore] = None, knowledge: Optional[KnowledgeProvider] = None) -> None:
        self.model=model
        self.registry=registry
        self.config=config or AgentConfig()
        self.run_store=run_store or InMemoryRunStore()
        self.knowledge=knowledge or NullKnowledgeProvider()
        self.executor=ToolExecutor(self.config.tool_timeout_seconds, allowed_permissions=self.config.allowed_permissions, confirm_sensitive=self.config.confirm_sensitive)

    def search_knowledge(self, query: str, *, limit: int = 5, filters: Optional[dict] = None) -> list:
        if not query.strip():
            raise ValueError("knowledge query cannot be empty")
        return self.knowledge.search(query, limit=limit, filters=filters)

    def run(self, task: str, context: Optional[RuntimeContext] = None) -> str:
        return self.run_result(task, context).output

    def run_result(self, task: str, context: Optional[RuntimeContext] = None) -> AgentResult:
        if not task.strip():
            raise ValueError("task cannot be empty")
        state=AgentState(task=task, messages=[{"role":"system","content":build_system_prompt(self.config.system_prompt, context)}, {"role":"user","content":task}])
        state.record("run_started", 0, task=task)
        self.run_store.save(state)
        return self._execute(state)

    def resume(self, run_id: str) -> str:
        return self.resume_result(run_id).output

    def cancel(self, run_id: str) -> AgentResult:
        state=self.run_store.get(run_id)
        if state is None: raise ValueError(f"run not found: {run_id}")
        if state.status=="completed": raise ValueError(f"run already completed: {run_id}")
        if state.status=="cancelled": return self._result(state)
        state.status="cancelled"; state.record("run_cancelled", state.step); self.run_store.save(state)
        return self._result(state)

    def resume_result(self, run_id: str) -> AgentResult:
        state=self.run_store.get(run_id)
        if state is None: raise ValueError(f"run not found: {run_id}")
        if state.status=="completed": raise ValueError(f"run already completed: {run_id}")
        if state.status=="running": raise ValueError(f"run is already active: {run_id}")
        if state.status=="cancelled": raise ValueError(f"run is cancelled: {run_id}")
        state.status="running"; state.record("run_resumed", state.step); self.run_store.save(state)
        return self._execute(state)

    def _execute(self, state: AgentState) -> AgentResult:
        tool_calls_count=0; consecutive_tool_errors=0
        for _ in range(self.config.max_steps):
            state.step+=1; state.record("model_step_started", state.step); self.run_store.save(state)
            response=self.model.chat(state.messages, self.registry.schemas()); calls=response.tool_calls or []
            if not calls:
                state.output=response.content or ""; state.status="completed"; state.record("run_completed", state.step, output=state.output); self.run_store.save(state); return self._result(state)
            state.messages.append({"role":"assistant","content":response.content,"tool_calls":[{"id":c.id,"name":c.name,"arguments":c.arguments} for c in calls]}); self.run_store.save(state)
            for call in calls:
                tool=self.registry.get(call.name); state.record("tool_call_started", state.step, tool=call.name); tool_calls_count+=1
                if tool_calls_count>self.config.max_tool_calls:
                    state.status="policy_limit"; state.output="Stopped: tool-call policy limit reached."; state.record("run_stopped", state.step, reason="max_tool_calls"); self.run_store.save(state); return self._result(state)
                result={"error":f"Unknown tool: {call.name}"} if tool is None else self.executor.execute(tool, call.arguments, self.config.tool_max_retries)
                consecutive_tool_errors=consecutive_tool_errors+1 if isinstance(result, dict) and "error" in result else 0
                state.log.append({"step":state.step,"tool":call.name,"arguments":call.arguments,"result":result})
                state.record("tool_call_completed", state.step, tool=call.name, result=result)
                state.messages.append({"role":"tool","tool_call_id":call.id,"content":json.dumps(result, default=str)}); self.run_store.save(state)
                if consecutive_tool_errors>=self.config.max_consecutive_tool_errors:
                    state.status="policy_limit"; state.output="Stopped: consecutive tool-error policy limit reached."; state.record("run_stopped", state.step, reason="max_consecutive_tool_errors"); self.run_store.save(state); return self._result(state)
        state.status="step_limit"; state.output="Stopped: step limit reached. Partial progress is available in the run log."; state.record("run_stopped", state.step, reason="step_limit"); self.run_store.save(state); return self._result(state)

    @staticmethod
    def _result(state: AgentState) -> AgentResult:
        return AgentResult(run_id=state.run_id,status=state.status,output=state.output,steps=state.step,events=[{"type":e.type,"timestamp":e.timestamp,"step":e.step,"data":e.data} for e in state.events])
