from core.memory import ConversationMemory


def test_memory_add_and_read():
    memory = ConversationMemory()
    memory.add({"role": "user", "content": "hello"})
    assert memory.messages() == [{"role": "user", "content": "hello"}]
    assert len(memory) == 1


def test_memory_returns_copy():
    memory = ConversationMemory([{"role": "user", "content": "hello"}])
    messages = memory.messages()
    messages.append({"role": "assistant", "content": "hi"})
    assert len(memory) == 1


def test_memory_clear():
    memory = ConversationMemory([{"role": "user", "content": "hello"}])
    memory.clear()
    assert memory.messages() == []
