"""Configured local-file knowledge provider."""

from __future__ import annotations

import asyncio
from pathlib import Path

from pharmacy_mcp.domain.models.provider import ProviderQuery, ProviderResult
from pharmacy_mcp.domain.models.response import SourceReference
from pharmacy_mcp.infrastructure.documents import DocumentStore
from pharmacy_mcp.infrastructure.providers.catalog import get_provider_descriptor


class FileKnowledgeProvider:
    descriptor = get_provider_descriptor("file")

    def __init__(
        self,
        roots: tuple[Path, ...],
        *,
        max_bytes: int,
        max_files: int,
    ) -> None:
        self.store = DocumentStore(
            roots,
            max_bytes=max_bytes,
            max_files=max_files,
        )

    async def query(self, request: ProviderQuery) -> ProviderResult:
        matches, warnings, scanned = await asyncio.to_thread(
            self.store.search,
            request.text,
            request.limit,
        )
        return ProviderResult(
            provider_id=self.descriptor.id,
            data={
                "matches": [match.__dict__ for match in matches],
                "files_scanned": scanned,
                "configured_roots": [str(root) for root in self.store.roots],
            },
            sources=[
                SourceReference(
                    provider="file",
                    title="Configured local pharmaceutical files",
                )
            ],
            warnings=warnings,
        )
