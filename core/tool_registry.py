from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

PERMISSIONS = ("read", "write", "sensitive")

@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    handler: Callable[..., Any]
    schema: Dict[str, Any]
    permission: str = "read"
    permission: str = "read"

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if not tool.name.strip():
            raise ValueError("Tool name cannot be empty")
        if tool.permission not in PERMISSIONS:
            raise ValueError(f"Invalid tool permission: {tool.permission}")
        if not isinstance(tool.schema, dict):
            raise ValueError("Tool schema must be a dictionary")
        if tool.permission not in ("read", "write", "sensitive"):
            raise ValueError(f"Invalid tool permission: {tool.permission}")
        if not isinstance(tool.schema, dict):
            raise ValueError("Tool schema must be a dictionary")
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.schema,
                "permission": t.permission,
            }
            for t in self._tools.values()
        ]

    def handlers(self) -> Dict[str, Callable[..., Any]]:
        return {name: tool.handler for name, tool in self._tools.items()}
