import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from .knowledge import KnowledgeItem


class SupabaseKnowledgeProvider:
    """Knowledge provider backed by the existing public.knowledge table."""

    def __init__(
        self,
        url: str,
        api_key: str,
        *,
        business_id: Optional[str] = None,
        table: str = "knowledge",
        timeout_seconds: float = 15.0,
    ) -> None:
        self.base_url = url.rstrip("/") + "/rest/v1"
        self.api_key = api_key
        self.business_id = business_id
        self.table = table
        self.timeout_seconds = timeout_seconds

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[KnowledgeItem]:
        if limit < 1:
            raise ValueError("limit must be at least 1")

        filters = dict(filters or {})
        if self.business_id is not None:
            filters.setdefault("business_id", self.business_id)

        params = {
            "select": "id,title,content,type,metadata",
            "limit": str(limit),
        }
        for key, value in filters.items():
            params[key] = f"eq.{value}"

        # V1 uses PostgREST filtering and lightweight text matching.
        # Semantic/vector retrieval can be added later without changing the interface.
        if query.strip():
            params["or"] = (
                f"(title.ilike.*{self._escape_like(query)}*,"
                f"content.ilike.*{self._escape_like(query)}*)"
            )

        query_string = urllib.parse.urlencode(params, safe="*,()")
        rows = self._request("GET", f"/{self.table}?{query_string}")

        return [
            KnowledgeItem(
                id=row["id"],
                title=row["title"],
                content=row["content"],
                source="supabase",
                knowledge_type=row.get("type", "document"),
                metadata=row.get("metadata") or {},
            )
            for row in rows
        ]

    @staticmethod
    def _escape_like(value: str) -> str:
        return value.replace("*", "").replace(",", " ").strip()

    def _request(self, method: str, path: str) -> Any:
        request = urllib.request.Request(
            self.base_url + path,
            method=method,
            headers={
                "apikey": self.api_key,
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload) if payload else []
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Supabase knowledge request failed ({exc.code}): {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Supabase knowledge request failed: {exc.reason}") from exc
