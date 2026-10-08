from core.state import AgentState
from core.store import InMemoryRunStore


def test_store_save_and_get_isolated_copy():
    store = InMemoryRunStore()
    state = AgentState(task="hello")
    state.messages.append({"role": "user", "content": "hello"})
    store.save(state)

    loaded = store.get(state.run_id)
    assert loaded is not None
    assert loaded.task == "hello"

    loaded.messages.append({"role": "assistant", "content": "changed"})
    loaded.step = 99

    again = store.get(state.run_id)
    assert again is not None
    assert len(again.messages) == 1
    assert again.step == 0


def test_store_returns_none_for_unknown_run():
    assert InMemoryRunStore().get("missing") is None

from core.store import JsonFileRunStore


def test_json_file_store_round_trip(tmp_path):
    store = JsonFileRunStore(tmp_path / "runs.json")
    state = AgentState(task="persist me")
    state.record("run_started", 0)
    store.save(state)
    loaded = store.get(state.run_id)
    assert loaded is not None
    assert loaded.task == "persist me"
    assert loaded.events[0].type == "run_started"


def test_json_file_store_lists_runs(tmp_path):
    store = JsonFileRunStore(tmp_path / "runs.json")
    first = AgentState(task="one")
    second = AgentState(task="two")
    store.save(first)
    store.save(second)
    assert {s.task for s in store.list()} == {"one", "two"}


from core.supabase_store import SupabaseRunStore


class FakeSupabaseRunStore(SupabaseRunStore):
    def __init__(self):
        super().__init__("https://example.supabase.co", "test-key", agent_id="agent-1")
        self.requests = []

    def _request(self, method, path, payload=None, *, extra_headers=None):
        self.requests.append((method, path, payload, extra_headers))
        if method == "GET":
            return [{
                "id": "run-1",
                "task": "persist me",
                "status": "completed",
                "steps": 2,
                "output": "done",
                "metadata": {
                    "messages": [{"role": "user", "content": "hello"}],
                    "log": [{"step": 1}],
                    "events": [{
                        "type": "run_started",
                        "timestamp": "2026-01-01T00:00:00+00:00",
                        "step": 0,
                        "data": {},
                    }],
                },
            }]
        return None


def test_supabase_store_save_builds_run_payload():
    store = FakeSupabaseRunStore()
    state = AgentState(task="persist me", run_id="run-1", status="completed", step=2, output="done")
    store.save(state)

    method, path, payload, headers = store.requests[0]
    assert method == "POST"
    assert path == "/runs?on_conflict=id"
    assert payload["id"] == "run-1"
    assert payload["agent_id"] == "agent-1"
    assert payload["status"] == "completed"
    assert headers["Prefer"].startswith("resolution=merge-duplicates")


def test_supabase_store_round_trip_mapping():
    store = FakeSupabaseRunStore()
    loaded = store.get("run-1")
    assert loaded is not None
    assert loaded.task == "persist me"
    assert loaded.status == "completed"
    assert loaded.step == 2
    assert loaded.output == "done"
    assert loaded.messages[0]["content"] == "hello"
    assert loaded.events[0].type == "run_started"


from core.conversation_store import SupabaseConversationStore


class FakeConversationStore(SupabaseConversationStore):
    def __init__(self):
        super().__init__("https://example.supabase.co", "test-key")
        self.calls = []

    def _request(self, method, path, payload=None, *, extra_headers=None):
        self.calls.append((method, path, payload, extra_headers))
        if method == "GET" and "/messages?" in path:
            return [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ]
        if method == "GET":
            return [{"id": "conversation-1", "status": "active"}]
        return [{"id": "new-record"}]


def test_conversation_store_creates_and_loads_memory():
    store = FakeConversationStore()
    conversation = store.create_conversation(
        business_id="business-1",
        agent_id="agent-1",
        channel="web",
    )
    assert conversation["id"] == "new-record"

    memory = store.load_memory("conversation-1")
    assert memory == [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]
