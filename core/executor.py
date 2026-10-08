import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any, Callable, Dict

class ToolExecutor:
    def __init__(self, timeout_seconds: float = 30.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")
        self.timeout_seconds = timeout_seconds

    def execute(self, name: str, arguments_json: str, tools: Dict[str, Callable[..., Any]]) -> Any:
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
                return pool.submit(tools[name], **args).result(timeout=self.timeout_seconds)
        except TimeoutError:
            return {"error": f"Tool '{name}' timed out after {self.timeout_seconds}s"}
        except Exception as exc:
            return {"error": f"Tool '{name}' failed: {exc}"}
