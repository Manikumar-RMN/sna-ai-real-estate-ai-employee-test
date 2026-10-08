from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional, Set


DEFAULT_SYSTEM_PROMPT = """You are an agent running inside the SNA AI Agent Engine.
Use tools when they are needed to complete the task.
Never invent tool results.
If a tool fails, inspect the error and decide whether to retry, use another tool, or explain the limitation.
Finish with a clear answer when the task is complete."""


@dataclass(frozen=True)
class AgentConfig:
    """Runtime configuration for one agent instance."""
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    max_steps: int = 8
    tool_timeout_seconds: float = 30.0
    allowed_permissions: Set[str] = field(default_factory=lambda: {"read"})
    confirm_sensitive: bool = False
    max_tool_calls: int = 32
    max_consecutive_tool_errors: int = 3

    def __post_init__(self) -> None:
        if self.max_steps < 1:
            raise ValueError("max_steps must be >= 1")
        if self.tool_timeout_seconds <= 0:
            raise ValueError("tool_timeout_seconds must be > 0")
        if self.max_tool_calls < 1:
            raise ValueError("max_tool_calls must be >= 1")
        if self.max_consecutive_tool_errors < 1:
            raise ValueError("max_consecutive_tool_errors must be >= 1")
        valid = {"read", "write", "sensitive"}
        invalid = set(self.allowed_permissions) - valid
        if invalid:
            raise ValueError(f"invalid permissions: {sorted(invalid)}")


@dataclass
class RuntimeContext:
    """Request-scoped context separate from conversation messages."""
    business_id: Optional[str] = None
    user_id: Optional[str] = None
    channel: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, object]:
        return {
            "business_id": self.business_id,
            "user_id": self.user_id,
            "channel": self.channel,
            "session_id": self.session_id,
            "metadata": dict(self.metadata),
        }


def build_system_prompt(base_prompt: str, context: Optional[RuntimeContext]) -> str:
    if context is None:
        return base_prompt
    return f"{base_prompt}\n\nRuntime context:\n{context.as_dict()}"
