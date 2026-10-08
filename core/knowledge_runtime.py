from typing import Any, Dict, List, Optional

from .knowledge import KnowledgeItem, KnowledgeProvider


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
