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
