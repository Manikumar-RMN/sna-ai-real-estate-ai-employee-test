from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol


@dataclass(frozen=True)
class KnowledgeItem:
    """A normalized piece of knowledge returned by any knowledge provider."""
    id: str
    title: str
    content: str
    source: str = "unknown"
    knowledge_type: str = "document"
    score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class KnowledgeProvider(Protocol):
    """Provider-neutral interface for pluggable knowledge retrieval."""

    def search(self, query: str, *, limit: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[KnowledgeItem]:
        ...


class CompositeKnowledgeProvider:
    """Search multiple knowledge providers and combine their results."""

    def __init__(self, providers: List[KnowledgeProvider]) -> None:
        self.providers = list(providers)

    def search(self, query: str, *, limit: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[KnowledgeItem]:
        if limit < 1:
            raise ValueError("limit must be at least 1")

        results: List[KnowledgeItem] = []
        for provider in self.providers:
            results.extend(provider.search(query, limit=limit, filters=filters))

        # Providers may return different ranking semantics. Preserve provider order
        # unless every result has a numeric score, in which case higher is better.
        if results and all(item.score is not None for item in results):
            results.sort(key=lambda item: item.score or 0.0, reverse=True)

        return results[:limit]
