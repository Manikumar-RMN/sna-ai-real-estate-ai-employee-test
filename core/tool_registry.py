from dataclasses import dataclass
from typing import Any, Callable, Dict, List

@dataclass
class Tool:
    name: str
    description: str
    handler: Callable[..., Any]
    schema: Dict[str, Any]

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def schemas(self) -> List[Dict[str, Any]]:
        return [
            {"name": t.name, "description": t.description, "input_schema": t.schema}
            for t in self._tools.values()
        ]

    def handlers(self) -> Dict[str, Callable[..., Any]]:
        return {name: tool.handler for name, tool in self._tools.items()}
