"""NLM MedlinePlus Connect medication-information client."""

from __future__ import annotations

from typing import Any

import httpx

from pharmacy_mcp.config import settings

RXNORM_OID = "2.16.840.1.113883.6.88"
NDC_OID = "2.16.840.1.113883.6.69"


class MedlinePlusClient:
    """Find patient-education pages by RxCUI, NDC, or English drug name."""

    def __init__(
        self,
        service_url: str | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.service_url = service_url or settings.medlineplus_service_url
        self.timeout = settings.request_timeout
        self.transport = transport

    async def search_medication(
        self,
        *,
        drug_name: str | None = None,
        code: str | None = None,
        code_system: str = "ndc",
        language: str = "en",
    ) -> list[dict[str, Any]]:
        """Return normalized MedlinePlus medication and topic links."""

        if not drug_name and not code:
            raise ValueError("drug_name or code is required")
        oid = RXNORM_OID if code_system.lower() == "rxcui" else NDC_OID
        params = {
            "mainSearchCriteria.v.cs": oid,
            "informationRecipient.languageCode.c": language,
            "knowledgeResponseType": "application/json",
        }
        if code:
            params["mainSearchCriteria.v.c"] = code
        if drug_name:
            params["mainSearchCriteria.v.dn"] = drug_name

        async with httpx.AsyncClient(
            timeout=self.timeout,
            transport=self.transport,
        ) as client:
            response = await client.get(self.service_url, params=params)
        response.raise_for_status()
        entries = response.json().get("feed", {}).get("entry", [])
        if isinstance(entries, dict):
            entries = [entries]
        return [_normalize_entry(entry) for entry in entries]


def _normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    links = entry.get("link", [])
    if isinstance(links, dict):
        links = [links]
    alternate = next(
        (link.get("href") for link in links if link.get("rel") == "alternate"),
        None,
    )
    return {
        "title": entry.get("title", {}).get("_value"),
        "url": alternate,
        "summary_html": entry.get("summary", {}).get("_value"),
        "updated": entry.get("updated", {}).get("_value"),
        "source": "MedlinePlus.gov",
    }
