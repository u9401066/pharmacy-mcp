"""Read-only hospital FHIR client for medication and inventory knowledge."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx

from pharmacy_mcp.config import settings

FHIR_RESOURCE_ALLOWLIST = frozenset(
    {
        "Basic",
        "InventoryItem",
        "InventoryReport",
        "Medication",
        "MedicationDispense",
        "MedicationKnowledge",
        "MedicationRequest",
        "SupplyDelivery",
        "SupplyRequest",
    }
)


@dataclass
class FHIRSearchBatch:
    """Bounded resources and non-fatal compatibility warnings."""

    resources: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class FHIRClient:
    """FHIR R4/R5 read client with static SMART/Bearer token support.

    Token acquisition remains the hospital deployment's responsibility. This
    client never accepts credentials through MCP tool arguments and never
    returns authorization headers in results.
    """

    def __init__(
        self,
        base_url: str | None = None,
        *,
        bearer_token: str | None = None,
        fhir_version: str | None = None,
        medication_resources: tuple[str, ...] | None = None,
        inventory_resources: tuple[str, ...] | None = None,
        verify_tls: bool | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        resolved_url = base_url or settings.fhir_base_url
        if not resolved_url:
            raise ValueError("PHARMACY_MCP_FHIR_BASE_URL is not configured")
        self.base_url = resolved_url.rstrip("/") + "/"
        configured_token = settings.fhir_bearer_token
        self.bearer_token = bearer_token or (
            configured_token.get_secret_value() if configured_token else None
        )
        self.fhir_version = fhir_version or settings.fhir_version
        self.medication_resources = medication_resources or _resource_list(
            settings.fhir_medication_resources
        )
        self.inventory_resources = inventory_resources or _resource_list(
            settings.fhir_inventory_resources
        )
        self.verify_tls = settings.fhir_verify_tls if verify_tls is None else verify_tls
        self.timeout = settings.fhir_timeout_seconds
        self.transport = transport
        _validate_resources(self.medication_resources + self.inventory_resources)

    async def capability_statement(self) -> dict[str, Any]:
        """Read the server CapabilityStatement from `[base]/metadata`."""

        response = await self._get("metadata", {})
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return payload

    async def search_medications(self, query: str, limit: int) -> FHIRSearchBatch:
        """Search Medication and MedicationKnowledge across R4/R5 servers."""

        return await self._search_group(
            self.medication_resources,
            lambda _resource_type: {
                "_count": str(limit),
                "code:text": query,
            },
        )

    async def search_inventory(self, query: str, limit: int) -> FHIRSearchBatch:
        """Search R5 inventory resources and R4 supply fallbacks."""

        def params(resource_type: str) -> dict[str, str]:
            if resource_type == "InventoryItem":
                return {"_count": str(limit), "code:text": query, "status": "active"}
            return {"_count": str(limit), "_text": query}

        return await self._search_group(self.inventory_resources, params)

    async def search_patient_medications(
        self,
        patient_id: str,
        limit: int,
    ) -> FHIRSearchBatch:
        """Search patient medication orders/dispenses only with explicit context."""

        resources = ("MedicationRequest", "MedicationDispense")
        return await self._search_group(
            resources,
            lambda _resource_type: {
                "_count": str(limit),
                "patient": patient_id,
            },
        )

    async def search_resource(
        self,
        resource_type: str,
        params: dict[str, str],
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Execute one bounded FHIR search and normalize its searchset Bundle."""

        _validate_resources((resource_type,))
        response = await self._get(resource_type, params)
        if response.status_code in {400, 404, 405}:
            return [], _operation_warning(resource_type, response)
        response.raise_for_status()
        payload = response.json()
        if payload.get("resourceType") != "Bundle":
            return [], f"{resource_type} search did not return a FHIR Bundle"
        entries = payload.get("entry", [])
        resources = [
            entry["resource"]
            for entry in entries
            if isinstance(entry, dict) and isinstance(entry.get("resource"), dict)
        ]
        return resources, None

    async def _search_group(
        self,
        resource_types: tuple[str, ...],
        params_factory: Callable[[str], dict[str, str]],
    ) -> FHIRSearchBatch:
        results = await asyncio.gather(
            *(
                self.search_resource(resource_type, params_factory(resource_type))
                for resource_type in resource_types
            ),
            return_exceptions=True,
        )
        batch = FHIRSearchBatch()
        for resource_type, result in zip(resource_types, results, strict=True):
            if isinstance(result, BaseException):
                batch.warnings.append(f"{resource_type} query failed: {result}")
                continue
            resources, warning = result
            batch.resources[resource_type] = resources
            if warning:
                batch.warnings.append(warning)
        return batch

    async def _get(
        self,
        path: str,
        params: dict[str, str],
    ) -> httpx.Response:
        headers = {
            "Accept": "application/fhir+json",
            "User-Agent": "pharmacy-mcp/0.9",
        }
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=self.timeout,
            verify=self.verify_tls,
            transport=self.transport,
        ) as client:
            return await client.get(path, params=params)


def _resource_list(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _validate_resources(resource_types: tuple[str, ...]) -> None:
    invalid = sorted(set(resource_types) - FHIR_RESOURCE_ALLOWLIST)
    if invalid:
        raise ValueError(f"FHIR resources are not allowlisted: {', '.join(invalid)}")


def _operation_warning(resource_type: str, response: httpx.Response) -> str:
    detail = ""
    try:
        issues = response.json().get("issue", [])
        if issues:
            detail = issues[0].get("diagnostics") or issues[0].get("details", {}).get(
                "text", ""
            )
    except ValueError:
        detail = ""
    suffix = f": {detail}" if detail else ""
    return f"{resource_type} unsupported or search rejected ({response.status_code}){suffix}"
