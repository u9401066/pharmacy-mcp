"""Tests for file, SQL, vector, and allowlisted web knowledge connectors."""

import sqlite3
from pathlib import Path

import httpx
import pytest
from docx import Document
from openpyxl import Workbook

from pharmacy_mcp.domain.models.provider import ProviderQuery
from pharmacy_mcp.infrastructure.documents import DocumentStore
from pharmacy_mcp.infrastructure.providers.file import FileKnowledgeProvider
from pharmacy_mcp.infrastructure.providers.sql import (
    SQLiteKnowledgeProvider,
    SQLTableMapping,
)
from pharmacy_mcp.infrastructure.providers.vector import (
    VectorKnowledgeProvider,
    VectorSearchClient,
)
from pharmacy_mcp.infrastructure.providers.web import WebKnowledgeProvider


@pytest.fixture
def document_root(tmp_path: Path) -> Path:
    (tmp_path / "guide.md").write_text(
        "# Anticoagulation\nWarfarin requires INR monitoring.",
        encoding="utf-8",
    )
    (tmp_path / "formulary.csv").write_text(
        "name,rule\nWarfarin,high alert\n",
        encoding="utf-8",
    )

    document = Document()
    document.add_paragraph("Warfarin DOCX guideline")
    document.save(tmp_path / "guideline.docx")

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["drug", "stock"])
    sheet.append(["Warfarin", 120])
    workbook.save(tmp_path / "inventory.xlsx")
    return tmp_path


@pytest.mark.asyncio
async def test_file_provider_searches_markdown_csv_docx_and_xlsx(
    document_root: Path,
) -> None:
    provider = FileKnowledgeProvider(
        (document_root,),
        max_bytes=1_000_000,
        max_files=20,
    )

    result = await provider.query(ProviderQuery(text="warfarin", limit=10))

    extensions = {match["extension"] for match in result.data["matches"]}
    assert extensions == {".csv", ".docx", ".md", ".xlsx"}
    assert result.data["files_scanned"] == 4


def test_document_store_rejects_symlink_escape(
    document_root: Path,
    tmp_path: Path,
) -> None:
    outside = tmp_path.parent / "outside-pharmacy-secret.md"
    outside.write_text("warfarin secret", encoding="utf-8")
    link = document_root / "escape.md"
    link.symlink_to(outside)
    store = DocumentStore((document_root,), max_bytes=1000, max_files=10)

    with pytest.raises(ValueError, match="outside an allowed root"):
        store.read(link)

    outside.unlink()


@pytest.mark.asyncio
async def test_sql_provider_uses_read_only_allowlisted_projection(tmp_path: Path) -> None:
    database = tmp_path / "hospital.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE medications (code TEXT, name TEXT, stock INTEGER, secret TEXT)"
        )
        connection.execute(
            "INSERT INTO medications VALUES (?, ?, ?, ?)",
            ("W001", "Warfarin", 42, "must-not-leak"),
        )
    provider = SQLiteKnowledgeProvider(
        database,
        (
            SQLTableMapping(
                table="medications",
                search_columns=("code", "name"),
                output_columns=("code", "name", "stock"),
            ),
        ),
    )

    result = await provider.query(ProviderQuery(text="warfarin"))

    row = result.data["tables"]["medications"][0]
    assert row == {"code": "W001", "name": "Warfarin", "stock": 42}


def test_sql_mapping_rejects_injection_identifier() -> None:
    with pytest.raises(ValueError, match="Unsafe SQL identifier"):
        SQLTableMapping(
            table="medications; DROP TABLE medications",
            search_columns=("name",),
            output_columns=("name",),
        )


@pytest.mark.asyncio
async def test_vector_gateway_receives_only_explicit_vector_filters() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer vector-secret"
        payload = request.content.decode()
        assert "ward-a" in payload
        assert "patient_id" not in payload
        return httpx.Response(
            200,
            json={"results": [{"id": "doc-1", "score": 0.98, "text": "Warfarin"}]},
        )

    provider = VectorKnowledgeProvider(
        VectorSearchClient(
            "https://vector.test/search",
            api_key="vector-secret",
            transport=httpx.MockTransport(handler),
        )
    )
    request = ProviderQuery(
        text="warfarin",
        context={"patient_id": "patient-1", "vector_filters": {"ward": "ward-a"}},
    )

    result = await provider.query(request)

    assert result.data["results"][0]["id"] == "doc-1"


@pytest.mark.asyncio
async def test_web_provider_fetches_only_preconfigured_https_pages() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://knowledge.test/warfarin"
        return httpx.Response(
            200,
            headers={"content-type": "text/html", "content-length": "70"},
            text="<html><body><h1>Warfarin</h1><p>Monitor INR.</p></body></html>",
        )

    provider = WebKnowledgeProvider(
        ("https://knowledge.test/warfarin",),
        max_bytes=1000,
        transport=httpx.MockTransport(handler),
    )

    result = await provider.query(ProviderQuery(text="INR"))

    assert result.data["matches"][0]["url"] == "https://knowledge.test/warfarin"
    assert "Monitor INR" in result.data["matches"][0]["snippet"]


def test_web_provider_rejects_non_https_or_credentialed_urls() -> None:
    with pytest.raises(ValueError, match="credential-free HTTPS"):
        WebKnowledgeProvider(("http://127.0.0.1/secret",), max_bytes=1000)
    with pytest.raises(ValueError, match="credential-free HTTPS"):
        WebKnowledgeProvider(("https://user@example.test/secret",), max_bytes=1000)
