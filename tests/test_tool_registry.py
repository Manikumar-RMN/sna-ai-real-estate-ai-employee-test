import pytest
from core.tool_registry import Tool, ToolRegistry


def test_register_and_schema():
    r = ToolRegistry()
    r.register(Tool("hello", "Say hello.", lambda name: f"Hello {name}", {"type": "object"}))
    assert r.get("hello") is not None
    assert r.schemas()[0]["name"] == "hello"
    assert r.schemas()[0]["permission"] == "read"


def test_duplicate_tool_rejected():
    r = ToolRegistry()
    t = Tool("hello", "Say hello.", lambda: "hi", {"type": "object"})
    r.register(t)
    with pytest.raises(ValueError):
        r.register(t)


def test_invalid_permission_rejected():
    r = ToolRegistry()
    with pytest.raises(ValueError):
        r.register(Tool("bad", "Bad", lambda: None, {"type": "object"}, "admin"))


def test_invalid_schema_rejected():
    r = ToolRegistry()
    with pytest.raises(ValueError):
        r.register(Tool("bad", "Bad", lambda: None, "not-a-dict"))
