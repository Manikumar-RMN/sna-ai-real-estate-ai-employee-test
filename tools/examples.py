def add(a: float, b: float) -> float:
    return a + b

ADD_TOOL_SCHEMA = {
    "type": "object",
    "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
    "required": ["a", "b"],
    "additionalProperties": False,
}
