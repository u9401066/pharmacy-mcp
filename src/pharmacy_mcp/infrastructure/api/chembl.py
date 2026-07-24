"""EMBL-EBI ChEMBL client for drug, target, and bioactivity discovery."""

from __future__ import annotations

from typing import Any

import httpx

from pharmacy_mcp.config import settings


class ChEMBLClient:
    """Query bounded ChEMBL molecule, mechanism, and activity projections."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or settings.chembl_base_url).rstrip("/") + "/"
        self.timeout = settings.request_timeout
        self.transport = transport

    async def search_molecules(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search drug-like molecules by name or identifier."""

        payload = await self._get("molecule/search.json", {"q": query, "limit": limit})
        molecules = payload.get("molecules", [])
        return [
            _project_molecule(item)
            for item in molecules[:limit]
            if isinstance(item, dict)
        ]

    async def get_mechanisms(
        self,
        chembl_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Return known mechanisms for one ChEMBL molecule."""

        payload = await self._get(
            "mechanism.json",
            {"molecule_chembl_id": chembl_id, "limit": limit},
        )
        mechanisms = payload.get("mechanisms", [])
        return [
            _project_mechanism(item)
            for item in mechanisms[:limit]
            if isinstance(item, dict)
        ]

    async def get_activities(
        self,
        chembl_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Return a bounded bioactivity sample for one ChEMBL molecule."""

        payload = await self._get(
            "activity.json",
            {"molecule_chembl_id": chembl_id, "limit": limit},
        )
        activities = payload.get("activities", [])
        return [
            _project_activity(item)
            for item in activities[:limit]
            if isinstance(item, dict)
        ]

    async def _get(
        self,
        path: str,
        params: dict[str, str | int],
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            transport=self.transport,
        ) as client:
            response = await client.get(path, params=params)
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return payload


def _project_molecule(record: dict[str, Any]) -> dict[str, Any]:
    properties = record.get("molecule_properties", {})
    properties = properties if isinstance(properties, dict) else {}
    structures = record.get("molecule_structures", {})
    structures = structures if isinstance(structures, dict) else {}
    synonyms = record.get("molecule_synonyms", [])
    synonyms = synonyms if isinstance(synonyms, list) else []
    return {
        "chembl_id": record.get("molecule_chembl_id"),
        "preferred_name": record.get("pref_name"),
        "molecule_type": record.get("molecule_type"),
        "maximum_phase": record.get("max_phase"),
        "first_approval": record.get("first_approval"),
        "oral": record.get("oral"),
        "parenteral": record.get("parenteral"),
        "topical": record.get("topical"),
        "molecular_formula": properties.get("full_molformula"),
        "molecular_weight": properties.get("full_mwt"),
        "alogp": properties.get("alogp"),
        "canonical_smiles": structures.get("canonical_smiles"),
        "standard_inchi_key": structures.get("standard_inchi_key"),
        "synonyms": [
            item.get("molecule_synonym")
            for item in synonyms[:20]
            if isinstance(item, dict) and item.get("molecule_synonym")
        ],
    }


def _project_mechanism(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "molecule_chembl_id": record.get("molecule_chembl_id"),
        "mechanism_of_action": record.get("mechanism_of_action"),
        "action_type": record.get("action_type"),
        "target_chembl_id": record.get("target_chembl_id"),
        "target_name": record.get("target_name"),
        "binding_site_name": record.get("binding_site_name"),
        "direct_interaction": record.get("direct_interaction"),
        "disease_efficacy": record.get("disease_efficacy"),
    }


def _project_activity(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "activity_id": record.get("activity_id"),
        "molecule_chembl_id": record.get("molecule_chembl_id"),
        "target_chembl_id": record.get("target_chembl_id"),
        "target_name": record.get("target_pref_name"),
        "target_type": record.get("target_type"),
        "assay_chembl_id": record.get("assay_chembl_id"),
        "assay_type": record.get("assay_type"),
        "standard_type": record.get("standard_type"),
        "standard_relation": record.get("standard_relation"),
        "standard_value": record.get("standard_value"),
        "standard_units": record.get("standard_units"),
        "pchembl_value": record.get("pchembl_value"),
        "data_validity_comment": record.get("data_validity_comment"),
    }
