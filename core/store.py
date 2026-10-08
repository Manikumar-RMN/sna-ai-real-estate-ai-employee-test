from copy import deepcopy
from typing import Dict, Optional, Protocol

from .state import AgentState


class RunStore(Protocol):
    """Persistence boundary for agent runs."""

    def save(self, state: AgentState) -> None:
        ...

    def get(self, run_id: str) -> Optional[AgentState]:
        ...


class InMemoryRunStore:
    """In-memory RunStore used for tests and local development."""

    def __init__(self) -> None:
        self._runs: Dict[str, AgentState] = {}

    def save(self, state: AgentState) -> None:
        self._runs[state.run_id] = deepcopy(state)

    def get(self, run_id: str) -> Optional[AgentState]:
        state = self._runs.get(run_id)
        return deepcopy(state) if state is not None else None
