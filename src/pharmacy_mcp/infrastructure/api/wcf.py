"""Bounded async SOAP/WCF client for operator-configured medication data."""

from __future__ import annotations

import asyncio
import html
import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx
from defusedxml.ElementTree import fromstring

_XML_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")


@dataclass(frozen=True)
class WCFDataset:
    """One bounded WCF dataset snapshot and cache metadata."""

    rows: list[dict[str, Any]]
    retrieved_at: str
    cache_hit: bool


class WCFClient:
    """Fetch one no-argument SOAP operation without publishing its contract."""

    def __init__(
        self,
        service_url: str,
        soap_action: str,
        operation: str,
        *,
        namespace: str = "http://tempuri.org/",
        verify_tls: bool = True,
        timeout: float = 60.0,
        cache_ttl_seconds: int = 300,
        max_bytes: int = 25 * 1024 * 1024,
        max_records: int = 100_000,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        parsed = urlparse(service_url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise ValueError("WCF service URL must be credential-free HTTPS")
        action = soap_action.strip().strip('"')
        if not action or "\r" in action or "\n" in action:
            raise ValueError("WCF SOAP action is invalid")
        if not _XML_NAME.fullmatch(operation):
            raise ValueError("WCF operation is not a safe XML name")
        if timeout <= 0 or cache_ttl_seconds < 0 or max_bytes <= 0 or max_records <= 0:
            raise ValueError("WCF limits must be positive")

        self.service_url = service_url
        self.soap_action = action
        self.operation = operation
        self.namespace = namespace
        self.verify_tls = verify_tls
        self.timeout = timeout
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_bytes = max_bytes
        self.max_records = max_records
        self.transport = transport
        self._cached: WCFDataset | None = None
        self._cached_monotonic = 0.0
        self._lock = asyncio.Lock()

    async def fetch(self) -> WCFDataset:
        """Return a cached snapshot or perform one bounded SOAP request."""

        if self._cache_is_fresh():
            return self._cache_hit()
        async with self._lock:
            if self._cache_is_fresh():
                return self._cache_hit()
            dataset = await self._fetch_uncached()
            self._cached = dataset
            self._cached_monotonic = time.monotonic()
            return dataset

    def _cache_is_fresh(self) -> bool:
        return self._cached is not None and (
            time.monotonic() - self._cached_monotonic < self.cache_ttl_seconds
        )

    def _cache_hit(self) -> WCFDataset:
        if self._cached is None:  # pragma: no cover - guarded by _cache_is_fresh
            raise RuntimeError("WCF cache is empty")
        return WCFDataset(
            rows=self._cached.rows,
            retrieved_at=self._cached.retrieved_at,
            cache_hit=True,
        )

    async def _fetch_uncached(self) -> WCFDataset:
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f'"{self.soap_action}"',
            "User-Agent": "pharmacy-mcp/1.0",
        }
        async with httpx.AsyncClient(
            timeout=self.timeout,
            verify=self.verify_tls,
            follow_redirects=False,
            trust_env=False,
            transport=self.transport,
        ) as client:
            response = await client.post(
                self.service_url,
                content=self._envelope(),
                headers=headers,
            )
        response.raise_for_status()
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > self.max_bytes:
            raise ValueError("WCF response exceeds configured byte limit")
        if len(response.content) > self.max_bytes:
            raise ValueError("WCF response exceeds configured byte limit")

        rows = self._parse_rows(response.content)
        if len(rows) > self.max_records:
            raise ValueError("WCF response exceeds configured record limit")
        return WCFDataset(
            rows=rows,
            retrieved_at=datetime.now(UTC).isoformat(),
            cache_hit=False,
        )

    def _envelope(self) -> bytes:
        namespace = html.escape(self.namespace, quote=True)
        return (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
            '<soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">'
            f"<wsa:Action>{html.escape(self.soap_action, quote=False)}</wsa:Action>"
            f"<wsa:To>{html.escape(self.service_url, quote=False)}</wsa:To>"
            "</soap:Header><soap:Body>"
            f'<{self.operation} xmlns="{namespace}" />'
            "</soap:Body></soap:Envelope>"
        ).encode()

    def _parse_rows(self, content: bytes) -> list[dict[str, Any]]:
        root = fromstring(content)
        expected = f"{self.operation}Result"
        result = next(
            (
                element
                for element in root.iter()
                if element.tag.rsplit("}", 1)[-1] == expected
            ),
            None,
        )
        if result is None or not result.text or not result.text.strip():
            raise ValueError(f"WCF response does not contain {expected}")
        payload = json.loads(html.unescape(result.text.strip()))
        if isinstance(payload, dict):
            for key in ("results", "data", "items"):
                if isinstance(payload.get(key), list):
                    payload = payload[key]
                    break
            else:
                payload = [payload]
        if not isinstance(payload, list):
            raise ValueError("WCF result JSON is not an object or array")
        rows = [row for row in payload if isinstance(row, dict)]
        if len(rows) != len(payload):
            raise ValueError("WCF result contains non-object records")
        return rows
