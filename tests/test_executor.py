from core.executor import ToolExecutor

def test_unknown_tool(): assert "Unknown tool" in ToolExecutor().execute("missing","{}",{})["error"]
def test_invalid_json(): assert "Invalid JSON" in ToolExecutor().execute("x","{",{"x":lambda:1})["error"]
def test_tool_exception(): assert "failed" in ToolExecutor().execute("boom","{}",{"boom":lambda: (_ for _ in ()).throw(RuntimeError("boom"))})["error"]
