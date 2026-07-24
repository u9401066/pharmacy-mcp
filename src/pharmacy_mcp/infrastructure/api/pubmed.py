"""NCBI PubMed E-utilities client for medication literature discovery."""

from __future__ import annotations

from typing import Any

import httpx

from pharmacy_mcp.config import settings


class PubMedClient:
    """Search PubMed and return bounded citation summaries."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        api_key: str | None = None,
        email: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or settings.pubmed_base_url).rstrip("/") + "/"
        configured_key = settings.ncbi_api_key
        self.api_key = api_key or (
            configured_key.get_secret_value() if configured_key else None
        )
        self.email = email or settings.ncbi_email
        self.timeout = settings.request_timeout
        self.transport = transport

    async def search_articles(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Run ESearch then ESummary for a bounded PubMed result set."""

        common = {
            "db": "pubmed",
            "retmode": "json",
            "tool": "pharmacy_mcp",
        }
        if self.api_key:
            common["api_key"] = self.api_key
        if self.email:
            common["email"] = self.email

        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            transport=self.transport,
        ) as client:
            search = await client.get(
                "esearch.fcgi",
                params={
                    **common,
                    "term": query,
                    "retmax": str(limit),
                    "sort": "relevance",
                },
            )
            search.raise_for_status()
            identifiers = search.json().get("esearchresult", {}).get("idlist", [])
            identifiers = [
                str(identifier)
                for identifier in identifiers[:limit]
                if str(identifier).isdigit()
            ]
            if not identifiers:
                return []

            summary = await client.get(
                "esummary.fcgi",
                params={**common, "id": ",".join(identifiers)},
            )
            summary.raise_for_status()

        result = summary.json().get("result", {})
        return [
            _project_summary(identifier, result.get(identifier, {}))
            for identifier in identifiers
            if isinstance(result.get(identifier), dict)
        ]


def _project_summary(pmid: str, record: dict[str, Any]) -> dict[str, Any]:
    """Normalize one PubMed DocSum without reproducing article text."""

    authors = record.get("authors", [])
    article_ids = record.get("articleids", [])
    doi = next(
        (
            item.get("value")
            for item in article_ids
            if isinstance(item, dict) and item.get("idtype") == "doi"
        ),
        None,
    )
    return {
        "pmid": pmid,
        "title": record.get("title"),
        "journal": record.get("fulljournalname") or record.get("source"),
        "publication_date": record.get("pubdate"),
        "publication_types": list(record.get("pubtype", []))[:10],
        "authors": [
            author.get("name")
            for author in authors[:20]
            if isinstance(author, dict) and author.get("name")
        ],
        "doi": doi,
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
    }
