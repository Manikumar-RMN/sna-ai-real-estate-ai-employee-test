from core.executor import ToolExecutor
from core.tool_registry import Tool


def make_tool(name="x", permission="read", schema=None, handler=lambda: 1):
    return Tool(name, "test", handler, schema or {"type": "object"}, permission)


def test_unknown_tool():
    result = ToolExecutor().execute(make_tool("missing"), "{}")
    assert result == 1


def test_invalid_json():
    result = ToolExecutor().execute(make_tool(), "{")
    assert "Invalid JSON" in result["error"]


def test_schema_validation():
    tool = make_tool(
        schema={
            "type": "object",
            "properties": {"a": {"type": "number"}},
            "required": ["a"],
            "additionalProperties": False,
        },
        handler=lambda a: a,
    )
    result = ToolExecutor().execute(tool, '{"a":"wrong"}')
    assert result["error"] == "Invalid tool arguments"


def test_tool_exception():
    def boom():
        raise RuntimeError("boom")

    result = ToolExecutor().execute(make_tool(handler=boom), "{}")
    assert "failed" in result["error"]


def test_write_permission_denied_by_default():
    result = ToolExecutor().execute(make_tool(permission="write"), "{}")
    assert "Permission denied" in result["error"]


def test_write_permission_allowed():
    result = ToolExecutor(allowed_permissions={"read", "write"}).execute(
        make_tool(permission="write"), "{}"
    )
    assert result == 1


def test_sensitive_requires_confirmation():
    result = ToolExecutor(
        allowed_permissions={"read", "sensitive"},
        confirm_sensitive=False,
    ).execute(make_tool(permission="sensitive"), "{}")
    assert "Confirmation required" in result["error"]


def test_sensitive_can_be_confirmed():
    result = ToolExecutor(
        allowed_permissions={"read", "sensitive"},
        confirm_sensitive=True,
    ).execute(make_tool(permission="sensitive"), "{}")
    assert result == 1

def test_retryable_tool_retries_after_failure():
    attempts = {"count": 0}

    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise RuntimeError("temporary")
        return "ok"

    result = ToolExecutor().execute(
        Tool("flaky", "test", flaky, {"type": "object"}, "read", "general", True),
        "{}",
        max_retries=1,
    )
    assert result == "ok"
    assert attempts["count"] == 1
