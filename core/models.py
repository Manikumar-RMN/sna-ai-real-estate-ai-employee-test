from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str

@dataclass
class ModelMessage:
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None

class ChatModel(Protocol):
    def chat(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> ModelMessage:
        ...
