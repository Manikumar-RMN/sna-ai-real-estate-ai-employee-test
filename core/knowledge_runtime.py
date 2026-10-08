from typing import Any, Dict, List, Optional, Protocol

from .knowledge import KnowledgeItem


class KnowledgeProvider(Protocol):
    """Provider-neutral interface for pluggable knowledge retrieval."""

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[KnowledgeItem]:
        ...


class NullKnowledgeProvider:
    """No-op provider used when an agent does not have knowledge configured."""

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[KnowledgeItem]:
        return []
