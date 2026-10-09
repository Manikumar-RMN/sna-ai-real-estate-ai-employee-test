"""Tenant-scoped, allowlisted HTTPS JSON client for integration adapters.

This module intentionally does not accept complete URLs from agent/model input.
The base URL and secret name are trusted application configuration; each request
supplies a tenant ID and a relative path. Production deployments should implement
SecretProvider using a managed secrets vault, not InMemorySecretProvider.
"""
from dataclasses import dataclass
import json
from typing import Any, Mapping, Optional, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlencode, urlsplit
from urllib.request import HTTPHandler, HTTPSHandler, HTTPRedirectHandler, Request, build_opener


class IntegrationRequestError(RuntimeError):
    """Sanitized integration failure safe to show to callers."""


class SecretProvider(Protocol):
    def get_secret(self, *, tenant_id: str, integration_name: str, secret_name: str) -> Optional[str]:
        """Resolve a secret in the context of one tenant and integration."""
        ...


class InMemorySecretProvider:
    """Simple tenant-scoped provider for tests and local development only."""

    def __init__(self, values: Optional[Mapping[tuple[str, str, str], str]] = None) -> None:
        self._values = dict(values or {})

    def set_secret(self, *, tenant_id: str, integration_name: str, secret_name: str, value: str) -> None:
        key = (tenant_id, integration_name, secret_name)
        if not all(isinstance(part, str) and part.strip() for part in key):
            raise ValueError("tenant, integration, and secret names must be non-empty")
        if not isinstance(value, str) or not value:
            raise ValueError("secret value must be a non-empty string")
        self._values[key] = value

    def get_secret(self, *, tenant_id: str, integration_name: str, secret_name: str) -> Optional[str]:
        return self._values.get((tenant_id, integration_name, secret_name))


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: bytes


class HttpTransport(Protocol):
    def send(self, *, url: str, method: str, headers: Mapping[str, str],
             body: Optional[bytes], timeout_seconds: float, max_response_bytes: int) -> HttpResponse:
        ...


class _NoRedirect(HTTPRedirectHandler):
    """urllib redirect handler: redirects are rejected to prevent credential forwarding."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class UrllibHttpTransport:
    """Small standard-library transport with bounded responses and no redirects."""

    def send(self, *, url: str, method: str, headers: Mapping[str, str],
             body: Optional[bytes], timeout_seconds: float, max_response_bytes: int) -> HttpResponse:
        opener = build_opener(_NoRedirect(), HTTPHandler(), HTTPSHandler())
        request = Request(url, data=body, headers=dict(headers), method=method)
        try:
            response = opener.open(request, timeout=timeout_seconds)
        except HTTPError as exc:
            # Never return the response body; it can contain vendor diagnostics or secrets.
            raise IntegrationRequestError(f"Integration returned HTTP {exc.code}.") from None
        except (URLError, TimeoutError, OSError):
            raise IntegrationRequestError("Integration request failed or timed out.") from None
        try:
            data = response.read(max_response_bytes + 1)
            status = response.status
        finally:
            response.close()
        if len(data) > max_response_bytes:
            raise IntegrationRequestError("Integration response exceeded the configured size limit.")
        return HttpResponse(status=status, body=data)


class TenantScopedHttpJsonClient:
    """JSON client bound to one configured origin and tenant-scoped bearer secret.

    This class does not itself authorize a tenant. The authenticated application
    must supply the correct tenant_id; never take it directly from an LLM tool call.
    """

    def __init__(
        self,
        *,
        integration_name: str,
        base_url: str,
        secret_provider: SecretProvider,
        secret_name: str = "access_token",
        transport: Optional[HttpTransport] = None,
        timeout_seconds: float = 8.0,
        max_response_bytes: int = 1_000_000,
        allow_insecure_http: bool = False,
    ) -> None:
        if not integration_name.strip() or not secret_name.strip():
            raise ValueError("integration and secret names must be non-empty")
        parsed = urlsplit(base_url)
        if parsed.scheme not in ({"https", "http"} if allow_insecure_http else {"https"}):
            raise ValueError("base URL must use HTTPS")
        if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("base URL must be an origin/path without credentials, query, or fragment")
        if parsed.port is not None and not (1 <= parsed.port <= 65535):
            raise ValueError("base URL port is invalid")
        if timeout_seconds <= 0 or timeout_seconds > 30:
            raise ValueError("timeout_seconds must be greater than 0 and at most 30")
        if max_response_bytes < 1 or max_response_bytes > 5_000_000:
            raise ValueError("max_response_bytes must be between 1 and 5,000,000")
        self.integration_name = integration_name
        self.base_url = base_url.rstrip("/")
        self.secret_provider = secret_provider
        self.secret_name = secret_name
        self.transport = transport or UrllibHttpTransport()
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes

    @staticmethod
    def _validate_relative_path(path: str) -> str:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("request path must be a non-empty relative path")
        parsed = urlsplit(path)
        if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or path.startswith(("/", "\\\\")):
            raise ValueError("request path must be relative and must not include query or fragment")
        decoded_segments = unquote(parsed.path).replace("\\\\", "/").split("/")
        if any(segment in {".", ".."} for segment in decoded_segments):
            raise ValueError("request path must not contain dot segments")
        return parsed.path

    def request(
        self,
        *,
        tenant_id: str,
        method: str,
        path: str,
        payload: Any = None,
        query: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise ValueError("tenant_id must be supplied by the authenticated application")
        method = method.upper() if isinstance(method, str) else ""
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise ValueError("unsupported HTTP method")
        relative_path = self._validate_relative_path(path)
        secret = self.secret_provider.get_secret(
            tenant_id=tenant_id,
            integration_name=self.integration_name,
            secret_name=self.secret_name,
        )
        if not secret:
            raise IntegrationRequestError("Integration credentials are not configured for this tenant.")

        url = f"{self.base_url}/{relative_path.lstrip('/')}"
        if query:
            url = f"{url}?{urlencode(query, doseq=True)}"
        body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = {"Accept": "application/json", "Authorization": f"Bearer {secret}"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        response = self.transport.send(
            url=url,
            method=method,
            headers=headers,
            body=body,
            timeout_seconds=self.timeout_seconds,
            max_response_bytes=self.max_response_bytes,
        )
        if response.status < 200 or response.status >= 300:
            raise IntegrationRequestError(f"Integration returned HTTP {response.status}.")
        if not response.body:
            return None
        try:
            return json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise IntegrationRequestError("Integration returned an invalid JSON response.") from None
