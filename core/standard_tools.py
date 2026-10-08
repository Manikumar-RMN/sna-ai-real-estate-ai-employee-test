from datetime import datetime, timezone
from typing import Any

from .tool_bundles import ToolBundle
from .tool_registry import Tool


def echo(message: str) -> dict[str, Any]:
    return {"message": message}


def get_current_time() -> dict[str, str]:
    return {"utc": datetime.now(timezone.utc).isoformat()}


def standard_tool_bundle() -> ToolBundle:
    return ToolBundle(
        name="standard",
        tools=(
            Tool(
                name="echo",
                description="Return the supplied message unchanged.",
                handler=echo,
                schema={
                    "type": "object",
                    "properties": {"message": {"type": "string"}},
                    "required": ["message"],
                    "additionalProperties": False,
                },
                category="utility",
            ),
            Tool(
                name="get_current_time",
                description="Return the current UTC time.",
                handler=get_current_time,
                schema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                category="utility",
            ),
        ),
    )
