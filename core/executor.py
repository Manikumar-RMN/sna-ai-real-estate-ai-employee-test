import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any, Iterable, Optional

from jsonschema import Draft202012Validator, ValidationError

from .tool_registry import Tool


class ToolExecutor:
    def __init__(
        self,
        timeout_seconds: float = 30.0,
        allowed_permissions: Optional[Iterable[str]] = None,
        confirm_sensitive: bool = False,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")
        self.timeout_seconds = timeout_seconds
        self.allowed_permissions = set(allowed_permissions or {"read"})
        self.confirm_sensitive = confirm_sensitive

    def execute(self, tool: Tool, arguments_json: str, max_retries: int = 0) -> Any:
        if tool.permission not in self.allowed_permissions:
            return {"error": f"Permission denied for tool '{tool.name}' ({tool.permission})"}
        if tool.permission == "sensitive" and not self.confirm_sensitive:
            return {"error": f"Confirmation required for sensitive tool '{tool.name}'"}

        try:
            args = json.loads(arguments_json or "{}")
        except json.JSONDecodeError as exc:
            return {"error": f"Invalid JSON arguments: {exc.msg}"}

        if not isinstance(args, dict):
            return {"error": "Tool arguments must be a JSON object"}

        try:
            Draft202012Validator(tool.schema).validate(args)
        except ValidationError as exc:
            return {"error": "Invalid tool arguments", "details": exc.message}

        attempts = max_retries + 1 if tool.retryable else 1
        last_error = None
        for _ in range(attempts):
            try:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    return pool.submit(tool.handler, **args).result(timeout=self.timeout_seconds)
            except TimeoutError:
                last_error = f"Tool '{tool.name}' timed out after {self.timeout_seconds}s"
            except Exception as exc:
                last_error = f"Tool '{tool.name}' failed: {exc}"
        return {"error": last_error or f"Tool '{tool.name}' failed"}
