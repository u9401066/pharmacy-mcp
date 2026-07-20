"""RxNorm API client."""

from typing import Any

import httpx

from pharmacy_mcp.config import settings
from pharmacy_mcp.domain.entities.drug import Drug, DrugConcept, DrugType


class RxNormClient:
    """Client for RxNorm REST API."""

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or settings.rxnorm_base_url
        self.timeout = settings.request_timeout

    async def search_by_name(
        self, name: str, max_results: int = 10
    ) -> list[DrugConcept]:
        """
        Search drugs by name.

        Args:
            name: Drug name to search
            max_results: Maximum number of results

        Returns:
            List of DrugConcept matches
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/drugs.json", params={"name": name}
            )
            response.raise_for_status()
            data = response.json()

        concepts = []
        drug_group = data.get("drugGroup", {})
        concept_group = drug_group.get("conceptGroup", [])

        for group in concept_group:
            for prop in group.get("conceptProperties", []):
                concepts.append(
                    DrugConcept(
                        rxcui=prop.get("rxcui", ""),
                        name=prop.get("name", ""),
                        synonym=prop.get("synonym"),
                        tty=prop.get("tty"),
                    )
                )
                if len(concepts) >= max_results:
                    return concepts

        return concepts

    async def get_by_rxcui(self, rxcui: str) -> Drug | None:
        """
        Get drug details by RxCUI.

        Args:
            rxcui: RxNorm Concept Unique Identifier

        Returns:
            Drug entity or None
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Get basic properties
            response = await client.get(
                f"{self.base_url}/rxcui/{rxcui}/properties.json"
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()

        properties = data.get("properties", {})
        if not properties:
            return None

        drug = Drug(
            rxcui=rxcui,
            name=properties.get("name", ""),
            drug_type=self._parse_drug_type(properties.get("tty", "")),
        )

        # Get additional info
        drug.drug_classes = await self.get_drug_classes(rxcui)

        return drug

    async def get_interactions(self, rxcui: str) -> list[dict[str, Any]]:
        """
        Get drug interactions for a given RxCUI.

        Note: The RxNorm Drug Interaction API was discontinued by NLM in 2025.
        This method now returns an empty list with an appropriate notice.

        Args:
            rxcui: RxNorm Concept Unique Identifier

        Returns:
            List of interaction data (empty - API discontinued)
        """
        del rxcui
        # RxNorm Drug Interaction API was discontinued by NLM in 2025
        # Return empty list - use local interaction database instead
        return []

    async def get_drug_classes(self, rxcui: str) -> list[str]:
        """Get unique RxClass names for a given RxCUI."""

        memberships = await self.get_drug_class_memberships(rxcui)
        names: list[str] = []
        for membership in memberships:
            class_name = membership.get("class_name")
            if class_name and class_name not in names:
                names.append(class_name)
        return names

    async def get_drug_class_memberships(
        self, rxcui: str
    ) -> list[dict[str, str | None]]:
        """Get structured RxClass membership, relation, and source metadata."""

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/rxclass/class/byRxcui.json", params={"rxcui": rxcui}
            )
            if response.status_code != 200:
                return []
            data = response.json()

        memberships: list[dict[str, str | None]] = []
        seen: set[tuple[str | None, ...]] = set()
        for entry in data.get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", []):
            if not isinstance(entry, dict):
                continue
            class_info = entry.get("rxclassMinConceptItem", {})
            if not isinstance(class_info, dict):
                continue
            membership = {
                "class_id": class_info.get("classId"),
                "class_name": class_info.get("className"),
                "class_type": class_info.get("classType"),
                "relation": entry.get("rela"),
                "relation_source": entry.get("relaSource"),
            }
            key = tuple(membership.values())
            if membership["class_name"] and key not in seen:
                memberships.append(membership)
                seen.add(key)

        return memberships

    def _parse_drug_type(self, tty: str) -> DrugType:
        """Parse term type to DrugType."""
        brand_types = {"BN", "BPCK", "SBD", "SBDC", "SBDF", "SBDG"}
        ingredient_types = {"IN", "MIN", "PIN"}

        if tty in brand_types:
            return DrugType.BRAND
        elif tty in ingredient_types:
            return DrugType.INGREDIENT
        else:
            return DrugType.GENERIC
