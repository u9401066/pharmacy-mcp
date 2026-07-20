"""Runtime registry for all executable knowledge-provider adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pharmacy_mcp.config import settings
from pharmacy_mcp.domain.models.provider import (
    KnowledgeProvider,
    ProviderDescriptor,
    QueryCapability,
)
from pharmacy_mcp.infrastructure.providers.builtin import (
    DailyMedKnowledgeProvider,
    FHIRKnowledgeProvider,
    FormularyKnowledgeProvider,
    MedlinePlusKnowledgeProvider,
    OpenFDAKnowledgeProvider,
    PubChemKnowledgeProvider,
    RxClassKnowledgeProvider,
    RxNormKnowledgeProvider,
    TaiwanKnowledgeProvider,
)
from pharmacy_mcp.infrastructure.providers.catalog import PROVIDER_CATALOG
from pharmacy_mcp.infrastructure.providers.file import FileKnowledgeProvider
from pharmacy_mcp.infrastructure.providers.sql import (
    SQLiteKnowledgeProvider,
    mappings_from_settings,
)
from pharmacy_mcp.infrastructure.providers.vector import (
    VectorKnowledgeProvider,
    VectorSearchClient,
)
from pharmacy_mcp.infrastructure.providers.web import WebKnowledgeProvider


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
            candidates = [
                (source_id, self._providers.get(source_id)) for source_id in source_ids
            ]
            missing = [
                source_id for source_id, provider in candidates if provider is None
            ]
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

    def catalog(self) -> list[dict[str, Any]]:
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
    registry.register(RxNormKnowledgeProvider())
    registry.register(RxClassKnowledgeProvider())
    registry.register(OpenFDAKnowledgeProvider())
    registry.register(DailyMedKnowledgeProvider())
    registry.register(PubChemKnowledgeProvider())
    registry.register(MedlinePlusKnowledgeProvider())
    if settings.fhir_base_url:
        registry.register(FHIRKnowledgeProvider())
    file_roots = tuple(
        Path(value.strip()) for value in settings.file_roots.split(",") if value.strip()
    )
    if file_roots:
        registry.register(
            FileKnowledgeProvider(
                file_roots,
                max_bytes=settings.file_max_bytes,
                max_files=settings.file_max_files,
            )
        )
    if settings.sql_database_path and settings.sql_tables:
        registry.register(
            SQLiteKnowledgeProvider(
                settings.sql_database_path,
                mappings_from_settings(settings.sql_tables),
            )
        )
    if settings.vector_search_url:
        vector_key = settings.vector_api_key
        registry.register(
            VectorKnowledgeProvider(
                VectorSearchClient(
                    settings.vector_search_url,
                    api_key=vector_key.get_secret_value() if vector_key else None,
                    verify_tls=settings.vector_verify_tls,
                )
            )
        )
    if settings.web_urls:
        registry.register(
            WebKnowledgeProvider(
                tuple(settings.web_urls),
                max_bytes=settings.web_max_bytes,
            )
        )
    registry.register(TaiwanKnowledgeProvider(), aliases=("tw-nhi",))
    registry.register(FormularyKnowledgeProvider())
    return registry
