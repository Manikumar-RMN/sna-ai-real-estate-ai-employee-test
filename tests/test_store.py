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
