import pytest
from core.tool_registry import Tool, ToolRegistry

def test_register_and_schema():
 r=ToolRegistry(); r.register(Tool("hello","Say hello.",lambda name:f"Hello {name}",{"type":"object"})); assert r.get("hello") is not None; assert r.schemas()[0]["name"]=="hello"
def test_duplicate_tool_rejected():
 r=ToolRegistry(); t=Tool("hello","Say hello.",lambda:"hi",{"type":"object"}); r.register(t)
 with pytest.raises(ValueError): r.register(t)
