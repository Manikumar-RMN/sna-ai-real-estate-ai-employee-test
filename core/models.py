from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str


@dataclass
class ModelResponse:
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None


class ChatModel(Protocol):
    def chat(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> ModelResponse:
        ...


@dataclass
class AgentResult:
    run_id: str
    status: str
    output: str
    steps: int
    events: List[Dict[str, Any]]


@dataclass
class ConversationContext:
    messages: List[Dict[str, Any]]
    metadata: Dict[str, Any]
