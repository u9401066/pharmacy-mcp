"""Tests for hospital FHIR medication and inventory integration."""

import httpx
import pytest

from pharmacy_mcp.application.services.connector_access import ConnectorAccessService
from pharmacy_mcp.config import settings
from pharmacy_mcp.domain.models.provider import ProviderQuery, QueryCapability
from pharmacy_mcp.domain.models.response import ResponseStatus
from pharmacy_mcp.infrastructure.api.fhir import FHIRClient
from pharmacy_mcp.infrastructure.providers.builtin import FHIRKnowledgeProvider
from pharmacy_mcp.infrastructure.providers.registry import (
    ProviderRegistry,
    build_default_registry,
)


@pytest.mark.asyncio
async def test_fhir_client_uses_bearer_without_returning_it() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer hospital-secret"
        assert request.headers["accept"] == "application/fhir+json"
        return httpx.Response(
            200,
            json={"resourceType": "CapabilityStatement", "fhirVersion": "4.0.1"},
        )

    client = FHIRClient(
        "https://hospital.test/fhir",
        bearer_token="hospital-secret",
        transport=httpx.MockTransport(handler),
    )

    result = await client.capability_statement()

    assert result["fhirVersion"] == "4.0.1"
    assert "hospital-secret" not in str(result)


@pytest.mark.asyncio
async def test_fhir_capability_projection_reports_pharmacy_contract() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/metadata")
        return httpx.Response(
            200,
            json={
                "resourceType": "CapabilityStatement",
                "status": "active",
                "kind": "instance",
                "fhirVersion": "4.0.1",
                "format": ["json"],
                "software": {"name": "Hospital FHIR", "version": "2"},
                "rest": [
                    {
                        "mode": "client",
                        "resource": [
                            {
                                "type": "SupplyDelivery",
                                "interaction": [{"code": "search-type"}],
                            }
                        ],
                    },
                    {
                        "mode": "server",
                        "interaction": [{"code": "search-system"}],
                        "resource": [
                            {
                                "type": "Medication",
                                "profile": "https://hospital.test/Medication",
                                "interaction": [
                                    {"code": "read"},
                                    {"code": "search-type"},
                                ],
                                "searchParam": [
                                    {
                                        "name": "code",
                                        "type": "token",
                                        "definition": "http://hl7.org/fhir/SearchParameter/Medication-code",
                                    }
                                ],
                            },
                            {"type": "Patient", "interaction": [{"code": "read"}]},
                        ],
                    },
                ],
            },
        )

    client = FHIRClient(
        "https://hospital.test/fhir",
        medication_resources=("Medication",),
        inventory_resources=("SupplyDelivery",),
        transport=httpx.MockTransport(handler),
    )

    result = await client.inspect_capabilities()

    assert result["reported_fhir_version"] == "4.0.1"
    assert result["resource_types"] == ["Medication", "Patient"]
    assert result["pharmacy_resources"][0]["resource_type"] == "Medication"
    assert result["pharmacy_resources"][0]["interactions"] == [
        "read",
        "search-type",
    ]
    assert result["unsupported_configured_resources"] == ["SupplyDelivery"]


@pytest.mark.asyncio
async def test_fhir_capability_service_preserves_partial_compatibility() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            200,
            json={
                "resourceType": "CapabilityStatement",
                "fhirVersion": "4.0.1",
                "status": "active",
                "rest": [
                    {
                        "mode": "server",
                        "resource": [
                            {
                                "type": "Medication",
                                "interaction": [{"code": "search-type"}],
                            }
                        ],
                    }
                ],
            },
        )

    client = FHIRClient(
        "https://hospital.test/fhir",
        medication_resources=("Medication",),
        inventory_resources=("SupplyDelivery",),
        transport=httpx.MockTransport(handler),
    )
    registry = ProviderRegistry()
    registry.register(FHIRKnowledgeProvider(client))

    result = await ConnectorAccessService(registry).inspect_fhir_server()

    assert result.status is ResponseStatus.PARTIAL
    assert result.data["configured"] is True
    assert result.data["unsupported_configured_resources"] == ["SupplyDelivery"]
    assert result.sources[0].provider == "fhir"


@pytest.mark.asyncio
async def test_fhir_capability_service_reports_unconfigured_provider() -> None:
    result = await ConnectorAccessService(ProviderRegistry()).inspect_fhir_server()

    assert result.status is ResponseStatus.ERROR
    assert result.errors[0].code == "fhir_provider_unavailable"


@pytest.mark.asyncio
async def test_fhir_search_preserves_standard_extensions_and_filters_bad_entries() -> (
    None
):
    async def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            200,
            json={
                "resourceType": "Bundle",
                "type": "searchset",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Medication",
                            "id": "med-1",
                            "code": {"text": "Warfarin"},
                            "extension": [
                                {
                                    "url": "https://hospital.test/fhir/StructureDefinition/local-code",
                                    "valueString": "HOSP-001",
                                }
                            ],
                            "hospitalCustomField": "preserved",
                        }
                    },
                    {"resource": {"resourceType": "Patient", "id": "wrong"}},
                    {"fullUrl": "missing-resource"},
                ],
            },
        )

    client = FHIRClient(
        "https://hospital.test/fhir",
        transport=httpx.MockTransport(handler),
    )

    resources, warning = await client.search_resource("Medication", {"_count": "5"})

    assert resources[0]["code"]["text"] == "Warfarin"
    assert resources[0]["extension"][0]["valueString"] == "HOSP-001"
    assert resources[0]["hospitalCustomField"] == "preserved"
    assert warning is not None
    assert "malformed" in warning
    assert "Patient" in warning


@pytest.mark.asyncio
async def test_fhir_inventory_falls_back_across_r4_and_r5_resources() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/InventoryItem"):
            return httpx.Response(
                404,
                json={
                    "resourceType": "OperationOutcome",
                    "issue": [{"diagnostics": "R5 resource not supported"}],
                },
            )
        assert request.url.path.endswith("/SupplyDelivery")
        return httpx.Response(
            200,
            json={
                "resourceType": "Bundle",
                "type": "searchset",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "SupplyDelivery",
                            "id": "stock-1",
                            "status": "completed",
                            "suppliedItem": {
                                "quantity": {"value": 120, "unit": "tablet"}
                            },
                        }
                    }
                ],
            },
        )

    client = FHIRClient(
        "https://hospital.test/fhir",
        inventory_resources=("InventoryItem", "SupplyDelivery"),
        transport=httpx.MockTransport(handler),
    )

    result = await client.search_inventory("warfarin", 5)

    assert result.resources["InventoryItem"] == []
    assert result.resources["SupplyDelivery"][0]["id"] == "stock-1"
    assert "R5 resource not supported" in result.warnings[0]


@pytest.mark.asyncio
async def test_fhir_provider_queries_patient_only_with_explicit_context() -> None:
    seen_paths: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        if request.url.path.endswith(("MedicationRequest", "MedicationDispense")):
            assert request.url.params["patient"] == "patient-123"
        return httpx.Response(200, json={"resourceType": "Bundle", "type": "searchset"})

    client = FHIRClient(
        "https://hospital.test/fhir",
        medication_resources=("Medication",),
        inventory_resources=("SupplyDelivery",),
        transport=httpx.MockTransport(handler),
    )
    provider = FHIRKnowledgeProvider(client)

    result = await provider.query(
        ProviderQuery(
            text="warfarin",
            capabilities=(QueryCapability.FORMULARY,),
            context={"patient_id": "patient-123"},
        )
    )

    assert result.status is ResponseStatus.OK
    assert any(path.endswith("/Medication") for path in seen_paths)
    assert any(path.endswith("/MedicationRequest") for path in seen_paths)
    assert any(path.endswith("/MedicationDispense") for path in seen_paths)


def test_default_registry_enables_fhir_only_when_base_url_is_set(monkeypatch) -> None:
    monkeypatch.setattr(settings, "fhir_base_url", "https://hospital.test/fhir")

    providers = {item["id"]: item for item in build_default_registry().catalog()}

    assert providers["fhir"]["state"] == "ready"
    assert providers["fhir"]["registered"] is True
