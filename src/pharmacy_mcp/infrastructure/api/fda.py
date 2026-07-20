"""FDA openFDA drug API client."""

from __future__ import annotations

from typing import Any

import httpx

from pharmacy_mcp.config import settings


class FDAClient:
    """Client for openFDA API."""

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or settings.fda_base_url
        self.timeout = settings.request_timeout

    async def search_drug_labels(
        self, drug_name: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Search drug labels by name.

        Args:
            drug_name: Drug name to search
            limit: Maximum number of results

        Returns:
            List of drug label data
        """
        term = self._quoted_term(drug_name)
        return await self._search_endpoint(
            "label",
            f'openfda.brand_name:"{term}" OR openfda.generic_name:"{term}"',
            limit,
        )

    async def get_adverse_events(
        self, drug_name: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Get adverse events for a drug.

        Args:
            drug_name: Drug name
            limit: Maximum number of results

        Returns:
            List of adverse event reports
        """
        term = self._quoted_term(drug_name)
        return await self._search_endpoint(
            "event",
            f'patient.drug.medicinalproduct:"{term}"',
            limit,
        )

    async def search_ndc(self, drug_name: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search the NDC Directory; an NDC does not imply FDA approval."""

        term = self._quoted_term(drug_name)
        return await self._search_endpoint(
            "ndc",
            f'brand_name:"{term}" OR generic_name:"{term}"',
            limit,
        )

    async def search_recalls(
        self, drug_name: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search public drug recall enforcement reports."""

        term = self._quoted_term(drug_name)
        return await self._search_endpoint(
            "enforcement",
            (
                f'openfda.brand_name:"{term}" OR '
                f'openfda.generic_name:"{term}" OR '
                f'product_description:"{term}"'
            ),
            limit,
        )

    async def search_approvals(
        self, drug_name: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search Drugs@FDA approval application records."""

        term = self._quoted_term(drug_name)
        return await self._search_endpoint(
            "drugsfda",
            (
                f'openfda.brand_name:"{term}" OR '
                f'openfda.generic_name:"{term}" OR '
                f'products.brand_name:"{term}"'
            ),
            min(limit, 99),
        )

    async def search_orange_book(
        self, drug_name: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search Orange Book products and therapeutic-equivalence data."""

        term = self._quoted_term(drug_name)
        return await self._search_endpoint(
            "orangebook",
            (
                f'products.active_ingredients.name:"{term}" OR '
                f'products.brand_name:"{term}"'
            ),
            limit,
        )

    async def search_shortages(
        self, drug_name: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search FDA's current and resolved drug shortage records."""

        term = self._quoted_term(drug_name)
        return await self._search_endpoint(
            "shortages",
            f'generic_name:"{term}" OR proprietary_name:"{term}"',
            limit,
        )

    async def _search_endpoint(
        self,
        endpoint: str,
        search: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Run one bounded openFDA endpoint query and normalize empty results."""

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/drug/{endpoint}.json",
                params={"search": search, "limit": limit},
            )
            if response.status_code == 404:
                return []
            response.raise_for_status()
            data: Any = response.json()

        if not isinstance(data, dict):
            return []
        results = data.get("results", [])
        if not isinstance(results, list):
            return []
        return [item for item in results if isinstance(item, dict)]

    @staticmethod
    def _quoted_term(value: str) -> str:
        """Escape the two characters significant inside an openFDA phrase."""

        return value.replace("\\", "\\\\").replace('"', '\\"')

    async def get_drug_interactions_from_label(
        self, drug_name: str
    ) -> dict[str, Any] | None:
        """
        Get drug interactions from label.

        Args:
            drug_name: Drug name

        Returns:
            Interaction section from label
        """
        labels = await self.search_drug_labels(drug_name, limit=1)
        if not labels:
            return None

        label = labels[0]
        return {
            "drug_interactions": label.get("drug_interactions", []),
            "contraindications": label.get("contraindications", []),
            "warnings": label.get("warnings", []),
            "precautions": label.get("precautions", []),
        }

    async def get_drug_label_sections(self, drug_name: str) -> dict[str, Any] | None:
        """
        Get all relevant sections from drug label.

        Args:
            drug_name: Drug name

        Returns:
            Dictionary of label sections
        """
        labels = await self.search_drug_labels(drug_name, limit=1)
        if not labels:
            return None

        label = labels[0]
        openfda = label.get("openfda", {})

        return {
            "brand_name": openfda.get("brand_name", []),
            "generic_name": openfda.get("generic_name", []),
            "manufacturer_name": openfda.get("manufacturer_name", []),
            "route": openfda.get("route", []),
            "substance_name": openfda.get("substance_name", []),
            # Clinical sections
            "indications_and_usage": label.get("indications_and_usage", []),
            "dosage_and_administration": label.get("dosage_and_administration", []),
            "contraindications": label.get("contraindications", []),
            "warnings": label.get("warnings", []),
            "warnings_and_cautions": label.get("warnings_and_cautions", []),
            "adverse_reactions": label.get("adverse_reactions", []),
            "drug_interactions": label.get("drug_interactions", []),
            # Pharmacology
            "clinical_pharmacology": label.get("clinical_pharmacology", []),
            "mechanism_of_action": label.get("mechanism_of_action", []),
            "pharmacokinetics": label.get("pharmacokinetics", []),
            # Special populations
            "use_in_specific_populations": label.get("use_in_specific_populations", []),
            "pediatric_use": label.get("pediatric_use", []),
            "geriatric_use": label.get("geriatric_use", []),
            "pregnancy": label.get("pregnancy", []),
            "nursing_mothers": label.get("nursing_mothers", []),
            # Other
            "overdosage": label.get("overdosage", []),
            "storage_and_handling": label.get("storage_and_handling", []),
        }
