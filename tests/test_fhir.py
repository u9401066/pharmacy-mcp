"""Tests for hospital FHIR medication and inventory integration."""

import httpx
import pytest

from pharmacy_mcp.config import settings
from pharmacy_mcp.domain.models.provider import ProviderQuery, QueryCapability
from pharmacy_mcp.domain.models.response import ResponseStatus
from pharmacy_mcp.infrastructure.api.fhir import FHIRClient
from pharmacy_mcp.infrastructure.providers.builtin import FHIRKnowledgeProvider
from pharmacy_mcp.infrastructure.providers.registry import build_default_registry


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

    providers = {
        item["id"]: item for item in build_default_registry().catalog()
    }

    assert providers["fhir"]["state"] == "ready"
    assert providers["fhir"]["registered"] is True
