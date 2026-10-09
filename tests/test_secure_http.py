import json

import pytest

from core.secure_http import (
    HttpResponse,
    InMemorySecretProvider,
    IntegrationRequestError,
    TenantScopedHttpJsonClient,
)


class FakeTransport:
    def __init__(self, response=None):
        self.response = response or HttpResponse(200, b'{"ok": true}')
        self.calls = []

    def send(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def build_client(*, transport=None, secrets=None, base_url="https://api.example.test/v1"):
    provider = secrets or InMemorySecretProvider({
        ("tenant-a", "crm", "access_token"): "token-a",
        ("tenant-b", "crm", "access_token"): "token-b",
    })
    return TenantScopedHttpJsonClient(
        integration_name="crm",
        base_url=base_url,
        secret_provider=provider,
        transport=transport or FakeTransport(),
    )


def test_request_uses_tenant_scoped_secret_and_fixed_origin():
    transport = FakeTransport()
    client = build_client(transport=transport)
    output = client.request(
        tenant_id="tenant-a", method="POST", path="contacts",
        payload={"name": "Asha"}, query={"active": "true"},
    )
    call = transport.calls[0]
    assert output == {"ok": True}
    assert call["url"] == "https://api.example.test/v1/contacts?active=true"
    assert call["headers"]["Authorization"] == "Bearer token-a"
    assert json.loads(call["body"]) == {"name": "Asha"}


def test_tenant_cannot_fall_back_to_another_tenants_secret():
    transport = FakeTransport()
    client = build_client(transport=transport)
    with pytest.raises(IntegrationRequestError, match="not configured"):
        client.request(tenant_id="tenant-c", method="GET", path="contacts")
    assert transport.calls == []


@pytest.mark.parametrize("base_url", [
    "http://api.example.test",
    "https://user:password@api.example.test",
    "https://api.example.test/path?token=secret",
    "file:///etc/passwd",
])
def test_rejects_unsafe_base_urls(base_url):
    with pytest.raises(ValueError):
        build_client(base_url=base_url)


@pytest.mark.parametrize("path", [
    "https://evil.example/path",
    "//evil.example/path",
    "../admin",
    "%2e%2e/admin",
    "contacts?next=https://evil.example",
    "contacts#fragment",
])
def test_rejects_non_relative_or_traversal_paths(path):
    transport = FakeTransport()
    with pytest.raises(ValueError):
        build_client(transport=transport).request(
            tenant_id="tenant-a", method="GET", path=path
        )
    assert transport.calls == []


def test_rejects_unsupported_methods():
    with pytest.raises(ValueError, match="unsupported"):
        build_client().request(tenant_id="tenant-a", method="TRACE", path="contacts")


def test_non_success_response_is_sanitized():
    transport = FakeTransport(HttpResponse(403, b'{"error":"token-a leaked"}'))
    with pytest.raises(IntegrationRequestError, match="HTTP 403") as error:
        build_client(transport=transport).request(
            tenant_id="tenant-a", method="GET", path="contacts"
        )
    assert "token-a" not in str(error.value)


def test_invalid_json_response_is_sanitized():
    transport = FakeTransport(HttpResponse(200, b"not-json"))
    with pytest.raises(IntegrationRequestError, match="invalid JSON"):
        build_client(transport=transport).request(
            tenant_id="tenant-a", method="GET", path="contacts"
        )


def test_insecure_http_can_only_be_enabled_explicitly():
    provider = InMemorySecretProvider({("t", "crm", "access_token"): "token"})
    with pytest.raises(ValueError, match="HTTPS"):
        TenantScopedHttpJsonClient(
            integration_name="crm", base_url="http://localhost:8000",
            secret_provider=provider, transport=FakeTransport(),
        )
    client = TenantScopedHttpJsonClient(
        integration_name="crm", base_url="http://localhost:8000",
        secret_provider=provider, transport=FakeTransport(), allow_insecure_http=True,
    )
    assert client.request(tenant_id="t", method="GET", path="health") == {"ok": True}


def test_public_path_validator_rejects_encoded_traversal():
    with pytest.raises(ValueError):
        TenantScopedHttpJsonClient.validate_relative_path("%2e%2e/secrets")
    assert TenantScopedHttpJsonClient.validate_relative_path("webhook/events") == "webhook/events"
