"""Configured local-file knowledge provider."""

from __future__ import annotations

import asyncio
from pathlib import Path

from pharmacy_mcp.domain.models.provider import ProviderQuery, ProviderResult
from pharmacy_mcp.domain.models.response import SourceReference
from pharmacy_mcp.infrastructure.documents import DocumentRead, DocumentStore
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
                    title=match.title,
                    uri=(
                        f"pharmacy-document://{match.document_id}"
                        f"#char={match.char_start}-{match.char_end}"
                    ),
                    version=match.text_sha256,
                )
                for match in matches
            ],
            warnings=warnings,
        )

    async def read_document(
        self,
        document_id: str,
        *,
        offset: int = 0,
        max_chars: int = 10_000,
    ) -> DocumentRead:
        """Read an exact bounded span by an opaque ID returned from search."""

        return await asyncio.to_thread(
            self.store.read_by_id,
            document_id,
            offset=offset,
            max_chars=max_chars,
        )
