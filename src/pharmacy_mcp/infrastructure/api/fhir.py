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
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("FHIR metadata did not return a JSON object")
        return payload

    async def inspect_capabilities(self) -> dict[str, Any]:
        """Return a bounded pharmacy-focused projection of CapabilityStatement."""

        payload = await self.capability_statement()
        if payload.get("resourceType") != "CapabilityStatement":
            raise ValueError("FHIR metadata did not return a CapabilityStatement")

        resource_types: set[str] = set()
        system_interactions: set[str] = set()
        pharmacy_resources: list[dict[str, Any]] = []
        for rest in _dict_items(payload.get("rest")):
            if rest.get("mode") != "server":
                continue
            for interaction in _dict_items(rest.get("interaction")):
                code = interaction.get("code")
                if isinstance(code, str):
                    system_interactions.add(code)
            for resource in _dict_items(rest.get("resource")):
                resource_type = resource.get("type")
                if not isinstance(resource_type, str):
                    continue
                resource_types.add(resource_type)
                if resource_type not in FHIR_RESOURCE_ALLOWLIST:
                    continue
                interactions = sorted(
                    code
                    for item in _dict_items(resource.get("interaction"))
                    if isinstance((code := item.get("code")), str)
                )
                search_parameters = [
                    {
                        "name": item.get("name"),
                        "type": item.get("type"),
                        "definition": item.get("definition"),
                    }
                    for item in _dict_items(resource.get("searchParam"))
                    if isinstance(item.get("name"), str)
                ]
                supported_profiles = _string_items(resource.get("supportedProfile"))
                pharmacy_resources.append(
                    {
                        "resource_type": resource_type,
                        "interactions": interactions,
                        "search_parameters": search_parameters,
                        "profile": resource.get("profile"),
                        "supported_profiles": supported_profiles,
                    }
                )

        configured_resources = sorted(
            set(self.medication_resources + self.inventory_resources)
        )
        unsupported = sorted(set(configured_resources) - resource_types)
        software = payload.get("software")
        implementation = payload.get("implementation")
        return {
            "server": self.base_url,
            "configured_fhir_version": self.fhir_version,
            "reported_fhir_version": payload.get("fhirVersion"),
            "status": payload.get("status"),
            "kind": payload.get("kind"),
            "formats": _string_items(payload.get("format")),
            "patch_formats": _string_items(payload.get("patchFormat")),
            "software": software if isinstance(software, dict) else None,
            "implementation": (
                implementation if isinstance(implementation, dict) else None
            ),
            "system_interactions": sorted(system_interactions),
            "resource_types": sorted(resource_types),
            "pharmacy_resources": sorted(
                pharmacy_resources,
                key=lambda item: str(item["resource_type"]),
            ),
            "configured_resources": configured_resources,
            "unsupported_configured_resources": unsupported,
        }

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
        if not isinstance(payload, dict):
            return [], f"{resource_type} search did not return a JSON object"
        if payload.get("resourceType") != "Bundle":
            return [], f"{resource_type} search did not return a FHIR Bundle"
        if payload.get("type") != "searchset":
            return [], f"{resource_type} search returned a non-searchset FHIR Bundle"
        entries = payload.get("entry", [])
        if not isinstance(entries, list):
            return [], f"{resource_type} search Bundle.entry is not an array"

        resources: list[dict[str, Any]] = []
        malformed_entries = 0
        mismatched_resources: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(
                (resource := entry.get("resource")), dict
            ):
                malformed_entries += 1
                continue
            returned_type = resource.get("resourceType")
            if returned_type != resource_type:
                mismatched_resources.add(str(returned_type or "missing-resourceType"))
                continue
            resources.append(resource)

        warnings: list[str] = []
        if malformed_entries:
            warnings.append(
                f"{resource_type} search ignored {malformed_entries} malformed entries"
            )
        if mismatched_resources:
            warnings.append(
                f"{resource_type} search ignored mismatched resource types: "
                f"{', '.join(sorted(mismatched_resources))}"
            )
        return resources, "; ".join(warnings) or None

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


def _dict_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_items(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


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
