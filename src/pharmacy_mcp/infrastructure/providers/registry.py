"""Runtime registry for all executable knowledge-provider adapters."""

from __future__ import annotations

from pharmacy_mcp.domain.models.provider import (
    KnowledgeProvider,
    ProviderDescriptor,
    QueryCapability,
)
from pharmacy_mcp.infrastructure.providers.builtin import (
    FormularyKnowledgeProvider,
    OpenFDAKnowledgeProvider,
    RxNormKnowledgeProvider,
    TaiwanKnowledgeProvider,
)
from pharmacy_mcp.infrastructure.providers.catalog import PROVIDER_CATALOG


class ProviderRegistry:
    """Register adapters and resolve them by capability or explicit source."""

    def __init__(self) -> None:
        self._providers: dict[str, KnowledgeProvider] = {}

    def register(
        self,
        provider: KnowledgeProvider,
        *,
        aliases: tuple[str, ...] = (),
    ) -> None:
        """Register one executable provider and optional catalog aliases."""

        provider_ids = (provider.descriptor.id, *aliases)
        duplicates = [key for key in provider_ids if key in self._providers]
        if duplicates:
            raise ValueError(f"Providers already registered: {', '.join(duplicates)}")
        for provider_id in provider_ids:
            self._providers[provider_id] = provider

    def resolve(
        self,
        *,
        source_ids: list[str] | None,
        capabilities: tuple[QueryCapability, ...],
    ) -> tuple[list[KnowledgeProvider], list[str]]:
        """Resolve unique executable providers and report unavailable source IDs."""

        if source_ids:
            candidates = [(source_id, self._providers.get(source_id)) for source_id in source_ids]
            missing = [source_id for source_id, provider in candidates if provider is None]
            providers = [provider for _, provider in candidates if provider is not None]
        else:
            missing = []
            providers = [
                provider
                for provider in self._providers.values()
                if provider.descriptor.enabled_by_default
                and set(provider.descriptor.capabilities).intersection(capabilities)
            ]

        unique: dict[str, KnowledgeProvider] = {}
        for provider in providers:
            unique[provider.descriptor.id] = provider
        return list(unique.values()), missing

    def catalog(self) -> list[dict[str, object]]:
        """Return the full catalog with actual runtime registration state."""

        registered_ids = set(self._providers)
        return [
            {
                **descriptor.model_dump(mode="json"),
                "registered": descriptor.id in registered_ids,
            }
            for descriptor in PROVIDER_CATALOG
        ]

    @property
    def descriptors(self) -> tuple[ProviderDescriptor, ...]:
        """Metadata for unique executable providers."""

        unique = {
            provider.descriptor.id: provider.descriptor
            for provider in self._providers.values()
        }
        return tuple(unique.values())


def build_default_registry() -> ProviderRegistry:
    """Build the batteries-included public/local provider registry."""

    registry = ProviderRegistry()
    registry.register(RxNormKnowledgeProvider(), aliases=("rxclass",))
    registry.register(OpenFDAKnowledgeProvider())
    registry.register(TaiwanKnowledgeProvider(), aliases=("tw-nhi",))
    registry.register(FormularyKnowledgeProvider())
    return registry
