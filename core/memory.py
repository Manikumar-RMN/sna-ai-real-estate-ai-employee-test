from typing import Any, Dict, List, Optional


class ConversationMemory:
    """Provider- and database-neutral conversation memory."""

    def __init__(self, messages: Optional[List[Dict[str, Any]]] = None) -> None:
        self._messages = list(messages or [])

    def add(self, message: Dict[str, Any]) -> None:
        self._messages.append(dict(message))

    def messages(self) -> List[Dict[str, Any]]:
        return [dict(message) for message in self._messages]

    def clear(self) -> None:
        self._messages.clear()

    def __len__(self) -> int:
        return len(self._messages)
