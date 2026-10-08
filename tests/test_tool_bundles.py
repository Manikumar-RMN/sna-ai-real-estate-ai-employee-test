import pytest

from core.tool_bundles import ToolBundle
from core.tool_registry import Tool, ToolRegistry


def make_tool(name, category="utility", permission="read"):
    return Tool(name, "test", lambda: name, {"type": "object"}, permission, category)


def test_bundle_registers_all_tools():
    registry = ToolRegistry()
    ToolBundle("utilities", (make_tool("one"), make_tool("two"))).register_into(registry)
    assert [tool.name for tool in registry.list_tools()] == ["one", "two"]


def test_bundle_rejects_duplicate_names():
    with pytest.raises(ValueError):
        ToolBundle("bad", (make_tool("one"), make_tool("one")))


def test_register_many_is_atomic_on_duplicate():
    registry = ToolRegistry()
    registry.register(make_tool("existing"))
    with pytest.raises(ValueError):
        registry.register_many([make_tool("new"), make_tool("existing")])
    assert [tool.name for tool in registry.list_tools()] == ["existing"]


def test_register_many_preserves_permissions():
    registry = ToolRegistry()
    registry.register_many([make_tool("read"), make_tool("write", permission="write")])
    assert registry.get("write").permission == "write"


def test_list_tools_can_filter_by_category_and_permission():
    registry = ToolRegistry()
    registry.register_many([
        make_tool("utility", category="utility"),
        make_tool("crm", category="crm"),
        make_tool("writer", category="crm", permission="write"),
    ])
    assert [tool.name for tool in registry.list_tools(category="crm")] == ["crm", "writer"]
    assert [tool.name for tool in registry.list_tools(permission="write")] == ["writer"]


def test_standard_bundle_has_provider_neutral_tools():
    from core.standard_tools import standard_tool_bundle
    registry = ToolRegistry()
    standard_tool_bundle().register_into(registry)
    assert registry.get("echo") is not None
    assert registry.get("get_current_time") is not None
    assert all(tool.category == "utility" for tool in registry.list_tools())
