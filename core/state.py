from dataclasses import dataclass, field
from typing import Any, Dict, List

@dataclass
class AgentState:
    task: str
    messages: List[Dict[str, Any]] = field(default_factory=list)
    step: int = 0
    done: bool = False
    log: List[Dict[str, Any]] = field(default_factory=list)
