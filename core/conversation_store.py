import json
import urllib.error
import urllib.request
from typing import Any, Optional


class SupabaseConversationStore:
    """Persistence boundary for conversations and messages in Supabase."""

    def __init__(self, url: str, api_key: str, *, timeout_seconds: float = 15.0) -> None:
        self.base_url = url.rstrip("/") + "/rest/v1"
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def create_conversation(
        self,
        *,
        business_id: str,
        agent_id: str,
        user_id: Optional[str] = None,
        channel: str = "internal",
        external_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        payload = {
            "business_id": business_id,
            "agent_id": agent_id,
            "user_id": user_id,
            "channel": channel,
            "external_id": external_id,
            "metadata": metadata or {},
        }
        rows = self._request(
            "POST",
            "/conversations",
            payload,
            extra_headers={"Prefer": "return=representation"},
        )
        return rows[0]

    def get_conversation(self, conversation_id: str) -> Optional[dict[str, Any]]:
        rows = self._request(
            "GET",
            f"/conversations?id=eq.{conversation_id}&select=*",
        )
        return rows[0] if rows else None

    def add_message(
        self,
        *,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        rows = self._request(
            "POST",
            "/messages",
            {
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "metadata": metadata or {},
            },
            extra_headers={"Prefer": "return=representation"},
        )
        return rows[0]

    def get_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        return self._request(
            "GET",
            f"/messages?conversation_id=eq.{conversation_id}&select=*&order=created_at.asc",
        )

    def load_memory(self, conversation_id: str) -> list[dict[str, Any]]:
        """Return messages in the engine's conversation format."""
        return [
            {"role": row["role"], "content": row["content"]}
            for row in self.get_messages(conversation_id)
        ]

    def _request(
        self,
        method: str,
        path: str,
        payload: Optional[dict[str, Any]] = None,
        *,
        extra_headers: Optional[dict[str, str]] = None,
    ) -> Any:
        headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        headers.update(extra_headers or {})
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Supabase request failed ({exc.code}): {detail}"
            ) from exc
