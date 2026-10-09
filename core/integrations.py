"""Provider-neutral integration contracts and registry for SNA AI.

Adapters belong outside the Agent core. Secrets should be resolved by the
application at runtime and must never be placed in public metadata or logs.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Protocol


@dataclass(frozen=True)
class IntegrationHealth:
    ok: bool
    message: str = ""


@dataclass(frozen=True)
class IntegrationDescriptor:
    name: str
    version: str = "1.0"
    description: str = ""
    capabilities: tuple[str, ...] = ()
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("integration name cannot be empty")
        if not self.version.strip():
            raise ValueError("integration version cannot be empty")
        if any(not capability.strip() for capability in self.capabilities):
            raise ValueError("integration capabilities cannot be empty")


class IntegrationAdapter(Protocol):
    @property
    def descriptor(self) -> IntegrationDescriptor:
        ...

    def health_check(self) -> IntegrationHealth:
        ...


class IntegrationRegistry:
    """In-process registry; it does not store credentials or make network calls."""

    def __init__(self) -> None:
        self._adapters: Dict[str, IntegrationAdapter] = {}

    @staticmethod
    def _validate(adapter: IntegrationAdapter) -> IntegrationDescriptor:
        descriptor = adapter.descriptor
        if not isinstance(descriptor, IntegrationDescriptor):
            raise ValueError("adapter descriptor must be an IntegrationDescriptor")
        if not descriptor.name.strip():
            raise ValueError("integration name cannot be empty")
        return descriptor

    def register(self, adapter: IntegrationAdapter) -> None:
        descriptor = self._validate(adapter)
        if descriptor.name in self._adapters:
            raise ValueError(f"integration already registered: {descriptor.name}")
        self._adapters[descriptor.name] = adapter

    def register_many(self, adapters: Iterable[IntegrationAdapter]) -> None:
        batch = list(adapters)
        seen = set()
        for adapter in batch:
            name = self._validate(adapter).name
            if name in seen or name in self._adapters:
                raise ValueError(f"integration already registered: {name}")
            seen.add(name)
        for adapter in batch:
            self._adapters[adapter.descriptor.name] = adapter

    def get(self, name: str) -> Optional[IntegrationAdapter]:
        return self._adapters.get(name)

    def list_integrations(self, *, capability: Optional[str] = None) -> List[IntegrationDescriptor]:
        descriptors = [adapter.descriptor for adapter in self._adapters.values()]
        if capability is not None:
            descriptors = [d for d in descriptors if capability in d.capabilities]
        return descriptors

    def health_check(self, name: str) -> IntegrationHealth:
        adapter = self.get(name)
        if adapter is None:
            raise ValueError(f"integration not found: {name}")
        result = adapter.health_check()
        if not isinstance(result, IntegrationHealth):
            raise TypeError("integration health_check must return IntegrationHealth")
        return result


@dataclass
class FunctionIntegration:
    """Small adapter helper for wrapping a function without external dependencies."""

    descriptor: IntegrationDescriptor
    check: Any = None

    def health_check(self) -> IntegrationHealth:
        if self.check is None:
            return IntegrationHealth(ok=True, message="Adapter registered; no live connectivity check configured.")
        result = self.check()
        if isinstance(result, IntegrationHealth):
            return result
        if isinstance(result, bool):
            return IntegrationHealth(ok=result, message="Healthy" if result else "Health check failed")
        raise TypeError("health check callback must return bool or IntegrationHealth")
