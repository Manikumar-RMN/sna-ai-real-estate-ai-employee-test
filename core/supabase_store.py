import json
import urllib.error
import urllib.request
from dataclasses import asdict
from typing import Any, Optional

from .state import AgentEvent, AgentState


class SupabaseRunStore:
    """RunStore backed by a Supabase PostgREST table.

    The adapter stores engine run state in public.runs. It is intentionally
    independent of Supabase SDKs so the engine remains provider-neutral.
    """

    def __init__(
        self,
        url: str,
        api_key: str,
        *,
        agent_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        table: str = "runs",
        timeout_seconds: float = 15.0,
    ) -> None:
        self.base_url = url.rstrip("/") + "/rest/v1"
        self.api_key = api_key
        self.agent_id = agent_id
        self.conversation_id = conversation_id
        self.table = table
        self.timeout_seconds = timeout_seconds

    def save(self, state: AgentState) -> None:
        payload = {
            "id": state.run_id,
            "conversation_id": self.conversation_id,
            "agent_id": self.agent_id,
            "task": state.task,
            "status": state.status,
            "steps": state.step,
            "output": state.output,
            "metadata": {
                "messages": state.messages,
                "log": state.log,
                "events": [asdict(event) for event in state.events],
            },
        }
        self._request(
            "POST",
            f"/{self.table}?on_conflict=id",
            payload,
            extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        )

    def get(self, run_id: str) -> Optional[AgentState]:
        rows = self._request(
            "GET",
            f"/{self.table}?id=eq.{run_id}&select=id,task,status,steps,output,metadata"
        )
        if not rows:
            return None
        return self._from_row(rows[0])

    def list(self) -> list[AgentState]:
        rows = self._request(
            "GET",
            f"/{self.table}?select=id,task,status,steps,output,metadata&order=started_at.desc"
        )
        return [self._from_row(row) for row in rows]

    @staticmethod
    def _from_row(row: dict[str, Any]) -> AgentState:
        metadata = row.get("metadata") or {}
        return AgentState(
            task=row["task"],
            run_id=row["id"],
            messages=metadata.get("messages", []),
            step=row.get("steps", 0),
            log=metadata.get("log", []),
            events=[AgentEvent(**event) for event in metadata.get("events", [])],
            status=row.get("status", "running"),
            output=row.get("output", ""),
        )

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
