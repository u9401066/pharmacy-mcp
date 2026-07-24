"""NLM DailyMed Structured Product Label v2 client."""

from __future__ import annotations

from typing import Any

import httpx

from pharmacy_mcp.config import settings


class DailyMedClient:
    """Read current SPL metadata from DailyMed's public v2 API."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or settings.dailymed_base_url).rstrip("/") + "/"
        self.timeout = settings.request_timeout
        self.transport = transport

    async def search_spls(
        self,
        drug_name: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Search current labels by drug name and return paging provenance."""

        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            transport=self.transport,
        ) as client:
            response = await client.get(
                "v2/spls.json",
                params={"drug_name": drug_name, "pagesize": limit},
            )
        if response.status_code == 404:
            return {"results": [], "metadata": {}}
        response.raise_for_status()
        payload = response.json()
        return {
            "results": payload.get("data", []),
            "metadata": payload.get("metadata", {}),
        }

    async def get_spl(self, set_id: str) -> dict[str, Any] | None:
        """Fetch one SPL document by DailyMed SET ID as JSON."""

        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            transport=self.transport,
        ) as client:
            response = await client.get(f"v2/spls/{set_id}.json")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return payload
