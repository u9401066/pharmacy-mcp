"""Tests for provider discovery and the unified query orchestrator."""

from typing import Any

import pytest

from pharmacy_mcp.application.services.unified_query import UnifiedQueryService
from pharmacy_mcp.domain.entities.drug import DrugConcept
from pharmacy_mcp.domain.models.provider import (
    ProviderDescriptor,
    ProviderKind,
    ProviderQuery,
    ProviderResult,
    ProviderState,
    QueryCapability,
)
from pharmacy_mcp.domain.models.response import ResponseStatus, SourceReference
from pharmacy_mcp.infrastructure.providers.builtin import (
    FormularyKnowledgeProvider,
    OpenFDAKnowledgeProvider,
    RxClassKnowledgeProvider,
)
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


class FakeRxClassClient:
    async def search_by_name(
        self, name: str, max_results: int = 10
    ) -> list[DrugConcept]:
        return [
            DrugConcept(rxcui="11289", name=name.title(), tty="IN"),
            DrugConcept(rxcui="missing", name="Missing", tty="IN"),
        ][:max_results]

    async def get_drug_class_memberships(
        self, rxcui: str
    ) -> list[dict[str, str | None]]:
        if rxcui == "missing":
            raise RuntimeError("offline")
        return [
            {
                "class_id": "N0000175503",
                "class_name": "Vitamin K Antagonists",
                "class_type": "MOA",
                "relation": "has_MoA",
                "relation_source": "MEDRT",
            }
        ]


class FakeOpenFDAClient:
    base_url = "https://fda.example"

    def __init__(self, *, fail_shortages: bool = False) -> None:
        self.calls: list[str] = []
        self.fail_shortages = fail_shortages

    async def search_drug_labels(
        self, drug_name: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        self.calls.append("labels")
        return [
            {
                "openfda": {"brand_name": [drug_name], "generic_name": [drug_name]},
                "dosage_and_administration": ["individualize"],
                "drug_interactions": ["monitor interactions"],
            }
        ][:limit]

    async def get_adverse_events(
        self, drug_name: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        self.calls.append("adverse_events")
        return [
            {
                "safetyreportid": "1",
                "patient": {
                    "reaction": [{"reactionmeddrapt": "Haemorrhage"}],
                    "drug": [{"medicinalproduct": drug_name}],
                },
            }
        ][:limit]

    async def search_ndc(self, drug_name: str, limit: int = 10) -> list[dict[str, Any]]:
        self.calls.append("ndc")
        return [{"product_ndc": "0001-0001", "generic_name": drug_name}][:limit]

    async def search_recalls(
        self, drug_name: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        self.calls.append("recalls")
        return [{"recall_number": "D-1", "product_description": drug_name}][:limit]

    async def search_approvals(
        self, drug_name: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        self.calls.append("approvals")
        return [{"application_number": "NDA001", "sponsor_name": drug_name}][:limit]

    async def search_orange_book(
        self, drug_name: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        self.calls.append("therapeutic_equivalence")
        return [
            {
                "approval_date": "19970326",
                "products": [
                    {
                        "brand_name": drug_name,
                        "application_number": "040145",
                        "reference_standard": False,
                    }
                ],
            }
        ][:limit]

    async def search_shortages(
        self, drug_name: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        self.calls.append("shortages")
        if self.fail_shortages:
            raise RuntimeError("offline")
        return [{"generic_name": drug_name, "status": "Current"}][:limit]


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
async def test_unified_query_preserves_provider_partial_status() -> None:
    provider = FakeProvider("partial", data=["warfarin"])

    async def partial_query(request: ProviderQuery) -> ProviderResult:
        del request
        return ProviderResult(
            provider_id="partial",
            status=ResponseStatus.PARTIAL,
            data=["warfarin"],
            warnings=["one endpoint was unavailable"],
        )

    provider.query = partial_query  # type: ignore[method-assign]
    registry = ProviderRegistry()
    registry.register(provider)

    result = await UnifiedQueryService(registry).query(
        text="warfarin", sources=["partial"]
    )

    assert result.status is ResponseStatus.PARTIAL
    assert result.warnings == ["one endpoint was unavailable"]


@pytest.mark.asyncio
async def test_local_formulary_implements_provider_port() -> None:
    provider = FormularyKnowledgeProvider()

    result = await provider.query(ProviderQuery(text="warfarin", limit=5))

    assert result.status is ResponseStatus.OK
    assert result.provider_id == "local-formulary"
    assert any(item["generic_name"] == "Warfarin" for item in result.data)


@pytest.mark.asyncio
async def test_rxclass_provider_executes_class_lookup_and_isolates_failures() -> None:
    provider = RxClassKnowledgeProvider(FakeRxClassClient())  # type: ignore[arg-type]

    result = await provider.query(ProviderQuery(text="warfarin", limit=2))

    assert result.provider_id == "rxclass"
    assert result.status is ResponseStatus.PARTIAL
    assert result.data[0]["classes"][0]["class_type"] == "MOA"
    assert result.data[0]["classes"][0]["relation_source"] == "MEDRT"
    assert result.data[1]["classes"] == []
    assert "RxCUI missing" in result.warnings[0]


@pytest.mark.asyncio
async def test_openfda_provider_routes_every_declared_endpoint() -> None:
    client = FakeOpenFDAClient()
    provider = OpenFDAKnowledgeProvider(client)  # type: ignore[arg-type]

    result = await provider.query(
        ProviderQuery(
            text="warfarin",
            capabilities=(
                QueryCapability.LABEL,
                QueryCapability.ADVERSE_EVENT,
                QueryCapability.NDC,
                QueryCapability.RECALL,
                QueryCapability.APPROVAL,
                QueryCapability.THERAPEUTIC_EQUIVALENCE,
                QueryCapability.SHORTAGE,
            ),
            limit=2,
        )
    )

    assert result.status is ResponseStatus.OK
    assert set(result.data) == {
        "labels",
        "adverse_events",
        "ndc",
        "recalls",
        "approvals",
        "therapeutic_equivalence",
        "shortages",
    }
    assert result.data["adverse_events"][0]["reactions"] == ["Haemorrhage"]
    assert result.data["ndc"][0]["product_ndc"] == "0001-0001"
    assert set(client.calls) == set(result.data)
    assert len(result.sources) == 7


@pytest.mark.asyncio
async def test_openfda_provider_keeps_success_when_one_endpoint_fails() -> None:
    provider = OpenFDAKnowledgeProvider(  # type: ignore[arg-type]
        FakeOpenFDAClient(fail_shortages=True)
    )

    result = await provider.query(
        ProviderQuery(
            text="warfarin",
            capabilities=(QueryCapability.LABEL, QueryCapability.SHORTAGE),
        )
    )

    assert result.status is ResponseStatus.PARTIAL
    assert "labels" in result.data and "shortages" not in result.data
    assert result.errors[0].code == "openfda_endpoint_error"


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
