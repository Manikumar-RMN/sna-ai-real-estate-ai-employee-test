from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional

PERMISSIONS = ("read", "write", "sensitive")


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    handler: Callable[..., Any]
    schema: Dict[str, Any]
    permission: str = "read"
    category: str = "general"
    retryable: bool = False


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    @staticmethod
    def _validate_tool(tool: Tool) -> None:
        if not tool.name.strip():
            raise ValueError("Tool name cannot be empty")
        if tool.permission not in PERMISSIONS:
            raise ValueError(f"Invalid tool permission: {tool.permission}")
        if not isinstance(tool.schema, dict):
            raise ValueError("Tool schema must be a dictionary")
        if not tool.category.strip():
            raise ValueError("Tool category cannot be empty")

    def register(self, tool: Tool) -> None:
        self._validate_tool(tool)
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def register_many(self, tools: Iterable[Tool]) -> None:
        batch = list(tools)
        seen = set()
        for tool in batch:
            self._validate_tool(tool)
            if tool.name in seen or tool.name in self._tools:
                raise ValueError(f"Tool already registered: {tool.name}")
            seen.add(tool.name)
        for tool in batch:
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
                "category": t.category,
            }
            for t in self._tools.values()
        ]

    def handlers(self) -> Dict[str, Callable[..., Any]]:
        return {name: tool.handler for name, tool in self._tools.items()}

    def list_tools(
        self,
        *,
        category: Optional[str] = None,
        permission: Optional[str] = None,
    ) -> List[Tool]:
        tools = list(self._tools.values())
        if category is not None:
            tools = [tool for tool in tools if tool.category == category]
        if permission is not None:
            tools = [tool for tool in tools if tool.permission == permission]
        return tools
