"""Allowlisted HTTPS web-document knowledge provider."""

from __future__ import annotations

import asyncio
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse

import httpx

from pharmacy_mcp.domain.models.provider import ProviderQuery, ProviderResult
from pharmacy_mcp.domain.models.response import ResponseStatus, SourceReference
from pharmacy_mcp.infrastructure.providers.catalog import get_provider_descriptor


class WebKnowledgeProvider:
    """Fetch only administrator-configured HTTPS URLs; agents cannot supply URLs."""

    descriptor = get_provider_descriptor("web")

    def __init__(
        self,
        urls: tuple[str, ...],
        *,
        max_bytes: int,
        timeout: float = 20.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.urls = tuple(_validated_url(url) for url in urls)
        self.max_bytes = max_bytes
        self.timeout = timeout
        self.transport = transport

    async def query(self, request: ProviderQuery) -> ProviderResult:
        fetched = await asyncio.gather(
            *(self._fetch(url) for url in self.urls),
            return_exceptions=True,
        )
        matches: list[dict[str, Any]] = []
        warnings: list[str] = []
        sources: list[SourceReference] = []
        for url, result in zip(self.urls, fetched, strict=True):
            if isinstance(result, BaseException):
                warnings.append(f"{url}: {result}")
                continue
            sources.append(SourceReference(provider="web", title=url, uri=url))
            snippet = _snippet(result, request.text)
            if snippet:
                matches.append({"url": url, "snippet": snippet})
            if len(matches) >= request.limit:
                break
        return ProviderResult(
            provider_id=self.descriptor.id,
            status=ResponseStatus.PARTIAL if warnings else ResponseStatus.OK,
            data={"matches": matches, "pages_fetched": len(sources)},
            sources=sources,
            warnings=warnings,
        )

    async def _fetch(self, url: str) -> str:
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=False,
            transport=self.transport,
        ) as client, client.stream(
            "GET", url, headers={"Accept": "text/html,text/plain"}
        ) as response:
            response.raise_for_status()
            content_length = int(response.headers.get("content-length", "0"))
            if content_length > self.max_bytes:
                raise ValueError(f"response exceeds {self.max_bytes} byte limit")
            chunks = bytearray()
            async for chunk in response.aiter_bytes():
                chunks.extend(chunk)
                if len(chunks) > self.max_bytes:
                    raise ValueError(f"response exceeds {self.max_bytes} byte limit")
        content_type = response.headers.get("content-type", "")
        text = chunks.decode(response.encoding or "utf-8", errors="replace")
        return _html_to_text(text) if "html" in content_type else text


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _html_to_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value)
    return " ".join(" ".join(parser.parts).split())


def _validated_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username:
        raise ValueError("web sources must be credential-free HTTPS URLs")
    return value


def _snippet(text: str, query: str, size: int = 500) -> str | None:
    index = text.casefold().find(query.casefold())
    if index < 0:
        return None
    start = max(0, index - size // 3)
    return text[start : start + size].strip()
