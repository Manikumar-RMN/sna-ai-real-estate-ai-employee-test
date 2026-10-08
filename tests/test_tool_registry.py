import pytest
from core.tool_registry import Tool, ToolRegistry

def test_register_and_schema():
    registry = ToolRegistry()
    registry.register(Tool(
        name="hello",
        description="Say hello.",
        handler=lambda name: f"Hello {name}",
        schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    ))
    assert registry.get("hello") is not None
    assert registry.schemas()[0]["name"] == "hello"

def test_duplicate_tool_rejected():
    registry = ToolRegistry()
    tool = Tool("hello", "Say hello.", lambda: "hi", {"type": "object"})
    registry.register(tool)
    with pytest.raises(ValueError):
        registry.register(tool)
