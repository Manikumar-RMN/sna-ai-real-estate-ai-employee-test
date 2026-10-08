import json

from core.models import ModelResponse
from core.openai_provider import OpenAICompatibleProvider


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_openai_provider_maps_text_response(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse({
            "choices": [{"message": {"content": "Hello", "tool_calls": []}}]
        })

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    provider = OpenAICompatibleProvider(
        "test-key",
        "test-model",
        base_url="https://example.test/v1",
    )
    result = provider.chat([{"role": "user", "content": "Hi"}], [])

    assert isinstance(result, ModelResponse)
    assert result.content == "Hello"
    assert result.tool_calls is None
    assert captured["request"].full_url == "https://example.test/v1/chat/completions"
    assert captured["timeout"] == 60.0


def test_openai_provider_maps_tool_calls(monkeypatch):
    payloads = []

    def fake_urlopen(request, timeout):
        payloads.append(json.loads(request.data.decode("utf-8")))
        return FakeResponse({
            "choices": [{
                "message": {
                    "content": None,
                    "tool_calls": [{
                        "id": "call-1",
                        "function": {
                            "name": "lookup",
                            "arguments": '{"id":"123"}',
                        },
                    }],
                }
            }]
        })

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    provider = OpenAICompatibleProvider("key", "model")
    result = provider.chat(
        [{"role": "user", "content": "Find it"}],
        [{
            "name": "lookup",
            "description": "Find a record",
            "input_schema": {
                "type": "object",
                "properties": {"id": {"type": "string"}},
            },
        }],
    )

    assert result.tool_calls[0].id == "call-1"
    assert result.tool_calls[0].name == "lookup"
    assert result.tool_calls[0].arguments == '{"id":"123"}'
    assert payloads[0]["tools"][0]["type"] == "function"
    assert payloads[0]["tools"][0]["function"]["name"] == "lookup"


def test_openai_provider_validates_configuration():
    try:
        OpenAICompatibleProvider("", "model")
    except ValueError as e:
        assert "api_key" in str(e)
    else:
        assert False
