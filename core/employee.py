from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .agent import Agent
from .config import AgentConfig, RuntimeContext
from .knowledge import KnowledgeProvider
from .models import AgentResult, ChatModel
from .store import InMemoryRunStore, RunStore
from .tool_registry import ToolRegistry


@dataclass(frozen=True)
class EmployeeDefinition:
    name: str
    role: str
    description: str = ""
    goals: tuple[str, ...] = ()
    instructions: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("employee name cannot be empty")
        if not self.role.strip():
            raise ValueError("employee role cannot be empty")


class AIEmployee:
    def __init__(
        self,
        definition: EmployeeDefinition,
        model: ChatModel,
        registry: ToolRegistry,
        *,
        config: Optional[AgentConfig] = None,
        run_store: Optional[RunStore] = None,
        knowledge: Optional[KnowledgeProvider] = None,
    ) -> None:
        self.definition = definition
        base = config or AgentConfig()
        prompt = self._build_prompt(base.system_prompt)
        employee_config = AgentConfig(
            system_prompt=prompt,
            max_steps=base.max_steps,
            tool_timeout_seconds=base.tool_timeout_seconds,
            allowed_permissions=base.allowed_permissions,
            confirm_sensitive=base.confirm_sensitive,
            max_tool_calls=base.max_tool_calls,
            max_consecutive_tool_errors=base.max_consecutive_tool_errors,
            tool_max_retries=base.tool_max_retries,
        )
        self.agent = Agent(
            model,
            registry,
            employee_config,
            run_store or InMemoryRunStore(),
            knowledge,
        )

    def _build_prompt(self, base: str) -> str:
        goals = "\n".join(f"- {goal}" for goal in self.definition.goals)
        if not goals:
            goals = "- Complete the user's task accurately."
        return (
            f"{base}\n\n"
            f"You are the AI employee: {self.definition.name}.\n"
            f"Role: {self.definition.role}.\n"
            f"Description: {self.definition.description}\n"
            f"Goals:\n{goals}\n"
            f"Employee instructions:\n"
            f"{self.definition.instructions or 'Follow the engine instructions and available tool permissions.'}"
        )

    def run(self, task: str, context: Optional[RuntimeContext] = None) -> str:
        return self.agent.run(task, context)

    def run_result(self, task: str, context: Optional[RuntimeContext] = None) -> AgentResult:
        return self.agent.run_result(task, context)

    def resume_result(self, run_id: str) -> AgentResult:
        return self.agent.resume_result(run_id)

    def cancel(self, run_id: str) -> AgentResult:
        return self.agent.cancel(run_id)

    def search_knowledge(self, query: str, *, limit: int = 5, filters: Optional[dict] = None) -> list:
        return self.agent.search_knowledge(query, limit=limit, filters=filters)
