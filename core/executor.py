import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any, Callable

class ToolExecutor:
    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self.timeout_seconds = timeout_seconds

    def execute(self, name: str, arguments_json: str, tools: dict[str, Callable[..., Any]]) -> Any:
        if name not in tools:
            return {"error": f"Unknown tool: {name}"}

        try:
            args = json.loads(arguments_json or "{}")
        except json.JSONDecodeError as exc:
            return {"error": f"Invalid JSON arguments: {exc.msg}"}

        if not isinstance(args, dict):
            return {"error": "Tool arguments must be a JSON object"}

        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(tools[name], **args)
                return future.result(timeout=self.timeout_seconds)
        except TimeoutError:
            return {"error": f"Tool '{name}' timed out after {self.timeout_seconds}s"}
        except Exception as exc:
            return {"error": str(exc)}
