"""ClinicalTrials.gov API v2 client for medication intervention studies."""

from __future__ import annotations

from typing import Any

import httpx

from pharmacy_mcp.config import settings


class ClinicalTrialsClient:
    """Search current study records by intervention name."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or settings.clinical_trials_base_url).rstrip(
            "/"
        ) + "/"
        self.timeout = settings.request_timeout
        self.transport = transport

    async def search_studies(
        self,
        intervention: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Return bounded protocol metadata for matching intervention studies."""

        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            transport=self.transport,
        ) as client:
            response = await client.get(
                "studies",
                params={
                    "query.intr": intervention,
                    "pageSize": str(limit),
                    "format": "json",
                },
            )
        response.raise_for_status()
        payload = response.json()
        studies = payload.get("studies", [])
        return {
            "results": [
                _project_study(study)
                for study in studies[:limit]
                if isinstance(study, dict)
            ],
            "next_page_available": bool(payload.get("nextPageToken")),
        }


def _project_study(study: dict[str, Any]) -> dict[str, Any]:
    protocol = study.get("protocolSection", {})
    identification = protocol.get("identificationModule", {})
    status = protocol.get("statusModule", {})
    conditions = protocol.get("conditionsModule", {})
    design = protocol.get("designModule", {})
    arms = protocol.get("armsInterventionsModule", {})
    sponsor = protocol.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})
    nct_id = identification.get("nctId")
    interventions = arms.get("interventions", [])
    return {
        "nct_id": nct_id,
        "brief_title": identification.get("briefTitle"),
        "official_title": identification.get("officialTitle"),
        "overall_status": status.get("overallStatus"),
        "start_date": status.get("startDateStruct", {}).get("date"),
        "completion_date": status.get("completionDateStruct", {}).get("date"),
        "study_type": design.get("studyType"),
        "phases": list(design.get("phases", []))[:10],
        "conditions": list(conditions.get("conditions", []))[:20],
        "interventions": [
            {
                "type": item.get("type"),
                "name": item.get("name"),
                "description": _bounded_text(item.get("description")),
            }
            for item in interventions[:20]
            if isinstance(item, dict)
        ],
        "lead_sponsor": sponsor.get("name"),
        "has_results": bool(study.get("hasResults")),
        "url": f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else None,
    }


def _bounded_text(value: object, limit: int = 500) -> str | None:
    if not isinstance(value, str):
        return None
    return value if len(value) <= limit else value[:limit] + "…"
