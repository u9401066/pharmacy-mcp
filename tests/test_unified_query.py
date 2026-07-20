"""Tests for provider discovery and the unified query orchestrator."""

from typing import Any

import pytest

from pharmacy_mcp.application.services.unified_query import UnifiedQueryService
from pharmacy_mcp.domain.models.provider import (
    ProviderDescriptor,
    ProviderKind,
    ProviderQuery,
    ProviderResult,
    ProviderState,
    QueryCapability,
)
from pharmacy_mcp.domain.models.response import ResponseStatus, SourceReference
from pharmacy_mcp.infrastructure.providers.builtin import FormularyKnowledgeProvider
from pharmacy_mcp.infrastructure.providers.catalog import PROVIDER_CATALOG
from pharmacy_mcp.infrastructure.providers.registry import ProviderRegistry
from pharmacy_mcp.presentation.server import _handle_tool


class FakeProvider:
    def __init__(
        self,
        provider_id: str,
        *,
        data: Any = None,
        error: Exception | None = None,
    ) -> None:
        self.descriptor = ProviderDescriptor(
            id=provider_id,
            title=provider_id,
            kind=ProviderKind.LOCAL,
            state=ProviderState.READY,
            capabilities=(QueryCapability.SEARCH,),
            enabled_by_default=True,
        )
        self.data = data
        self.error = error

    async def query(self, request: ProviderQuery) -> ProviderResult:
        if self.error:
            raise self.error
        return ProviderResult(
            provider_id=self.descriptor.id,
            data={"query": request.text, "value": self.data},
            sources=[
                SourceReference(
                    provider=self.descriptor.id,
                    title=self.descriptor.title,
                )
            ],
        )


def test_catalog_ids_are_unique_and_states_are_explicit() -> None:
    provider_ids = [provider.id for provider in PROVIDER_CATALOG]

    assert len(provider_ids) == len(set(provider_ids))
    assert {"rxnorm", "openfda", "tw-tfda", "tw-nhi", "fhir"}.issubset(provider_ids)
    assert all(provider.state for provider in PROVIDER_CATALOG)


@pytest.mark.asyncio
async def test_unified_query_preserves_success_when_one_provider_fails() -> None:
    registry = ProviderRegistry()
    registry.register(FakeProvider("good", data=["warfarin"]))
    registry.register(FakeProvider("bad", error=RuntimeError("offline")))
    service = UnifiedQueryService(registry, provider_timeout=0.1)

    result = await service.query(text="warfarin", sources=["good", "bad"])

    assert result.status is ResponseStatus.PARTIAL
    assert result.data["provider_results"]["good"]["value"] == ["warfarin"]
    assert result.errors[0].provider == "bad"
    assert result.errors[0].code == "provider_error"


@pytest.mark.asyncio
async def test_unified_query_reports_unconfigured_provider() -> None:
    service = UnifiedQueryService(ProviderRegistry(), provider_timeout=0.1)

    result = await service.query(text="warfarin", sources=["drugbank"])

    assert result.status is ResponseStatus.ERROR
    assert result.errors[0].code == "provider_unavailable"
    assert result.data["provider_results"] == {}


@pytest.mark.asyncio
async def test_local_formulary_implements_provider_port() -> None:
    provider = FormularyKnowledgeProvider()

    result = await provider.query(ProviderQuery(text="warfarin", limit=5))

    assert result.status is ResponseStatus.OK
    assert result.provider_id == "local-formulary"
    assert any(item["generic_name"] == "Warfarin" for item in result.data)


@pytest.mark.asyncio
async def test_source_discovery_exposes_registration_truth() -> None:
    result = await _handle_tool(
        "list_knowledge_sources",
        {"capability": "inventory"},
    )

    assert isinstance(result, dict)
    assert result["count"] >= 2
    providers = {item["id"]: item for item in result["providers"]}
    assert providers["fhir"]["registered"] is False
    assert providers["fhir"]["state"] == "ready"


@pytest.mark.asyncio
async def test_query_pharmacy_routes_to_explicit_local_source() -> None:
    result = await _handle_tool(
        "query_pharmacy",
        {
            "query": "warfarin",
            "sources": ["local-formulary"],
            "capabilities": ["formulary"],
            "limit": 5,
        },
    )

    assert result.status is ResponseStatus.OK
    payload = result.data["provider_results"]["local-formulary"]
    assert payload[0]["generic_name"] == "Warfarin"
