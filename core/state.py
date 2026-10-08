from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4


@dataclass
class AgentEvent:
    type: str
    timestamp: str
    step: int
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentState:
    task: str
    run_id: str = field(default_factory=lambda: str(uuid4()))
    messages: List[Dict[str, Any]] = field(default_factory=list)
    step: int = 0
    log: List[Dict[str, Any]] = field(default_factory=list)
    events: List[AgentEvent] = field(default_factory=list)
    status: str = "running"
    output: str = ""

    def record(self, event_type: str, step: int, **data: Any) -> None:
        self.events.append(AgentEvent(
            type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            step=step,
            data=data,
        ))
