"""Configured vector-search HTTP gateway provider."""

from __future__ import annotations

from typing import Any

import httpx

from pharmacy_mcp.domain.models.provider import ProviderQuery, ProviderResult
from pharmacy_mcp.domain.models.response import SourceReference
from pharmacy_mcp.infrastructure.providers.catalog import get_provider_descriptor


class VectorSearchClient:
    """Small vendor-neutral contract for an organization's vector gateway."""

    def __init__(
        self,
        search_url: str,
        *,
        api_key: str | None = None,
        verify_tls: bool = True,
        timeout: float = 20.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.search_url = search_url
        self.api_key = api_key
        self.verify_tls = verify_tls
        self.timeout = timeout
        self.transport = transport

    async def search(
        self,
        query: str,
        limit: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        async with httpx.AsyncClient(
            timeout=self.timeout,
            verify=self.verify_tls,
            transport=self.transport,
        ) as client:
            response = await client.post(
                self.search_url,
                headers=headers,
                json={"query": query, "limit": limit, "filters": filters or {}},
            )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results", payload) if isinstance(payload, dict) else payload
        if not isinstance(results, list):
            raise ValueError("Vector gateway must return a list or {'results': [...]} object")
        return [item for item in results if isinstance(item, dict)][:limit]


class VectorKnowledgeProvider:
    descriptor = get_provider_descriptor("vector")

    def __init__(self, client: VectorSearchClient) -> None:
        self.client = client

    async def query(self, request: ProviderQuery) -> ProviderResult:
        filters = request.context.get("vector_filters")
        safe_filters = filters if isinstance(filters, dict) else None
        results = await self.client.search(request.text, request.limit, safe_filters)
        return ProviderResult(
            provider_id=self.descriptor.id,
            data={"results": results},
            sources=[
                SourceReference(
                    provider="vector",
                    title="Configured vector search gateway",
                    uri=self.client.search_url,
                )
            ],
        )
