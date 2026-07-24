"""Open Targets Platform GraphQL client for drug-target knowledge."""

from __future__ import annotations

from typing import Any

import httpx

from pharmacy_mcp.config import settings

_SEARCH_QUERY = """
query SearchDrugs($queryString: String!, $page: Pagination!) {
  search(queryString: $queryString, entityNames: [\"drug\"], page: $page) {
    total
    hits { id name description entity }
  }
}
"""

_DRUG_QUERY = """
query Drug($chemblId: String!) {
  drug(chemblId: $chemblId) {
    id name description drugType maximumClinicalStage
    synonyms { label source }
    tradeNames { label source }
    mechanismsOfAction {
      rows {
        actionType mechanismOfAction
        targets { id approvedSymbol approvedName }
      }
    }
    indications {
      count rows { disease { id name } maxClinicalStage }
    }
  }
}
"""


class OpenTargetsClient:
    """Search Open Targets drugs and fetch bounded mechanism/indication details."""

    def __init__(
        self,
        graphql_url: str | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.graphql_url = graphql_url or settings.open_targets_graphql_url
        self.timeout = settings.request_timeout
        self.transport = transport

    async def search_drugs(
        self,
        query: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Return matching drugs plus details for at most five top hits."""

        search_data = await self._graphql(
            _SEARCH_QUERY,
            {"queryString": query, "page": {"index": 0, "size": limit}},
        )
        search = search_data.get("search") or {}
        hits = search.get("hits", []) if isinstance(search, dict) else []
        projected_hits = [
            _project_hit(hit) for hit in hits[:limit] if isinstance(hit, dict)
        ]
        details: list[dict[str, Any]] = []
        for hit in projected_hits[:5]:
            identifier = hit.get("id")
            if not isinstance(identifier, str) or not identifier.startswith("CHEMBL"):
                continue
            detail_data = await self._graphql(_DRUG_QUERY, {"chemblId": identifier})
            drug = detail_data.get("drug")
            if isinstance(drug, dict):
                details.append(_project_drug(drug))
        return {
            "total": search.get("total") if isinstance(search, dict) else None,
            "hits": projected_hits,
            "details": details,
        }

    async def _graphql(
        self,
        query: str,
        variables: dict[str, object],
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(
            timeout=self.timeout,
            transport=self.transport,
        ) as client:
            response = await client.post(
                self.graphql_url,
                json={"query": query, "variables": variables},
            )
        response.raise_for_status()
        payload = response.json()
        errors = payload.get("errors")
        if errors:
            raise RuntimeError(f"Open Targets GraphQL error: {str(errors)[:500]}")
        data = payload.get("data")
        return data if isinstance(data, dict) else {}


def _project_hit(hit: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": hit.get("id"),
        "name": hit.get("name"),
        "description": _bounded_text(hit.get("description")),
        "entity": hit.get("entity"),
    }


def _project_drug(drug: dict[str, Any]) -> dict[str, Any]:
    mechanisms = drug.get("mechanismsOfAction") or {}
    mechanism_rows = mechanisms.get("rows", []) if isinstance(mechanisms, dict) else []
    indications = drug.get("indications") or {}
    indication_rows = (
        indications.get("rows", []) if isinstance(indications, dict) else []
    )
    return {
        "id": drug.get("id"),
        "name": drug.get("name"),
        "description": _bounded_text(drug.get("description")),
        "drug_type": drug.get("drugType"),
        "maximum_clinical_stage": drug.get("maximumClinicalStage"),
        "synonyms": _project_names(drug.get("synonyms")),
        "trade_names": _project_names(drug.get("tradeNames")),
        "mechanisms_of_action": [
            {
                "action_type": row.get("actionType"),
                "mechanism_of_action": row.get("mechanismOfAction"),
                "targets": [
                    {
                        "id": target.get("id"),
                        "approved_symbol": target.get("approvedSymbol"),
                        "approved_name": target.get("approvedName"),
                    }
                    for target in row.get("targets", [])[:20]
                    if isinstance(target, dict)
                ],
            }
            for row in mechanism_rows[:20]
            if isinstance(row, dict)
        ],
        "indication_count": indications.get("count")
        if isinstance(indications, dict)
        else None,
        "indications": [
            {
                "disease_id": row.get("disease", {}).get("id"),
                "disease_name": row.get("disease", {}).get("name"),
                "maximum_clinical_stage": row.get("maxClinicalStage"),
            }
            for row in indication_rows[:25]
            if isinstance(row, dict) and isinstance(row.get("disease"), dict)
        ],
    }


def _project_names(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [
        {"label": item.get("label"), "source": item.get("source")}
        for item in value[:20]
        if isinstance(item, dict)
    ]


def _bounded_text(value: object, limit: int = 1_000) -> str | None:
    if not isinstance(value, str):
        return None
    return value if len(value) <= limit else value[:limit] + "…"
