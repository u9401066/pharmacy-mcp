"""Operator-configured SOAP/WCF medication knowledge provider."""

from __future__ import annotations

from typing import Any

from pharmacy_mcp.domain.models.provider import ProviderQuery, ProviderResult
from pharmacy_mcp.domain.models.response import SourceReference
from pharmacy_mcp.infrastructure.api.wcf import WCFClient
from pharmacy_mcp.infrastructure.providers.catalog import get_provider_descriptor


class WCFKnowledgeProvider:
    """Search an internal WCF snapshot through explicit field allowlists."""

    descriptor = get_provider_descriptor("wcf")

    def __init__(
        self,
        client: WCFClient,
        *,
        search_fields: tuple[str, ...],
        output_fields: tuple[str, ...],
    ) -> None:
        if not search_fields or not output_fields:
            raise ValueError("WCF search and output field allowlists are required")
        self.client = client
        self.search_fields = search_fields
        self.output_fields = output_fields

    async def query(self, request: ProviderQuery) -> ProviderResult:
        dataset = await self.client.fetch()
        needle = request.text.casefold().strip()
        matched = [
            row
            for row in dataset.rows
            if any(
                needle in _search_text(row.get(field)) for field in self.search_fields
            )
        ]
        projected = [
            {field: row.get(field) for field in self.output_fields}
            for row in matched[: request.limit]
        ]
        return ProviderResult(
            provider_id=self.descriptor.id,
            data={
                "matches": projected,
                "match_count": len(matched),
                "records_scanned": len(dataset.rows),
                "cache_hit": dataset.cache_hit,
            },
            sources=[
                SourceReference(
                    provider="wcf",
                    title="Configured internal WCF medication service",
                    retrieved_at=dataset.retrieved_at,
                )
            ],
        )


def _search_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return ""
    return str(value).casefold()
