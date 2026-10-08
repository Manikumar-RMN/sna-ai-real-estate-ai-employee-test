import json
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Optional, Protocol

from .state import AgentEvent, AgentState


class RunStore(Protocol):
    """Persistence boundary for agent runs."""

    def save(self, state: AgentState) -> None:
        ...

    def get(self, run_id: str) -> Optional[AgentState]:
        ...

    def list(self) -> list[AgentState]:
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

    def list(self) -> list[AgentState]:
        return deepcopy(list(self._runs.values()))


class JsonFileRunStore:
    """Simple durable JSON-file RunStore for local deployments."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def save(self, state: AgentState) -> None:
        data = self._load()
        data[state.run_id] = asdict(state)
        self.path.write_text(json.dumps(data, default=str, indent=2), encoding="utf-8")

    def get(self, run_id: str) -> Optional[AgentState]:
        raw = self._load().get(run_id)
        return self._from_dict(raw) if raw else None

    def list(self) -> list[AgentState]:
        return [self._from_dict(raw) for raw in self._load().values()]

    def _load(self) -> dict:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _from_dict(raw: dict) -> AgentState:
        return AgentState(
            task=raw["task"],
            run_id=raw["run_id"],
            messages=raw.get("messages", []),
            step=raw.get("step", 0),
            log=raw.get("log", []),
            events=[AgentEvent(**event) for event in raw.get("events", [])],
            status=raw.get("status", "running"),
            output=raw.get("output", ""),
        )
