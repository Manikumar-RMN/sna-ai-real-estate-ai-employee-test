from core.executor import ToolExecutor

def test_unknown_tool():
    result = ToolExecutor().execute("missing", "{}", {})
    assert "Unknown tool" in result["error"]

def test_invalid_json():
    result = ToolExecutor().execute("x", "{", {"x": lambda: 1})
    assert "Invalid JSON" in result["error"]

def test_tool_exception():
    def boom():
        raise RuntimeError("boom")
    result = ToolExecutor().execute("boom", "{}", {"boom": boom})
    assert result["error"] == "boom"
