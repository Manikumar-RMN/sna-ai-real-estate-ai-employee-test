from dataclasses import dataclass
from typing import Protocol, Tuple

from .tool_registry import Tool, ToolRegistry


class ToolSet(Protocol):
    def tools(self) -> list[Tool]:
        """Return the tools provided by this tool set."""


@dataclass(frozen=True)
class ToolBundle:
    name: str
    tools: Tuple[Tool, ...]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Tool bundle name cannot be empty")
        names = [tool.name for tool in self.tools]
        if len(names) != len(set(names)):
            raise ValueError("Tool bundle contains duplicate tool names")

    def register_into(self, registry: ToolRegistry) -> None:
        registry.register_many(self.tools)
