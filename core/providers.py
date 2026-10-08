from typing import Any, Dict, List

from .models import ChatModel, ModelResponse


class ModelProvider:
    """Adapter boundary for any LLM provider."""

    def __init__(self, model: ChatModel) -> None:
        self.model = model

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ) -> ModelResponse:
        return self.model.chat(messages, tools)


class FunctionModelProvider(ModelProvider):
    """Small adapter for tests and lightweight local integrations."""

    pass
