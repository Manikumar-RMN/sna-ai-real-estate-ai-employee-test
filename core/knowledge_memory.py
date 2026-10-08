from typing import Any, Dict, List, Optional

from .knowledge import KnowledgeItem


class InMemoryKnowledgeProvider:
    """Simple local provider useful for tests, demos, and small deployments."""

    def __init__(self, items: Optional[List[KnowledgeItem]] = None) -> None:
        self._items = list(items or [])

    def add(self, item: KnowledgeItem) -> None:
        self._items.append(item)

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[KnowledgeItem]:
        if limit < 1:
            raise ValueError("limit must be at least 1")

        terms = [term.lower() for term in query.split() if term.strip()]
        filters = filters or {}

        matches = []
        for item in self._items:
            if any(getattr(item, key, item.metadata.get(key)) != value for key, value in filters.items()):
                continue

            haystack = f"{item.title} {item.content}".lower()
            score = sum(1 for term in terms if term in haystack)
            if score:
                matches.append(
                    KnowledgeItem(
                        id=item.id,
                        title=item.title,
                        content=item.content,
                        source=item.source,
                        knowledge_type=item.knowledge_type,
                        score=float(score),
                        metadata=dict(item.metadata),
                    )
                )

        matches.sort(key=lambda item: item.score or 0.0, reverse=True)
        return matches[:limit]
