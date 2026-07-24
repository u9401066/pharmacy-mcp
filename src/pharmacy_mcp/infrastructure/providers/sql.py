"""Read-only, allowlisted SQLite pharmaceutical knowledge provider."""

from __future__ import annotations

import asyncio
import re
import sqlite3
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from pharmacy_mcp.domain.models.provider import ProviderQuery, ProviderResult
from pharmacy_mcp.domain.models.response import SourceReference
from pharmacy_mcp.infrastructure.providers.catalog import get_provider_descriptor

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class SQLTableMapping(BaseModel):
    """Administrator allowlist for one searchable table projection."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    table: str
    search_columns: tuple[str, ...] = Field(min_length=1)
    output_columns: tuple[str, ...] = Field(min_length=1)

    @field_validator("table")
    @classmethod
    def validate_table(cls, value: str) -> str:
        return _validated_identifier(value)

    @field_validator("search_columns", "output_columns")
    @classmethod
    def validate_columns(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_validated_identifier(value) for value in values)


class SQLiteKnowledgeProvider:
    """Search configured columns without exposing raw SQL to agents."""

    descriptor = get_provider_descriptor("sql")

    def __init__(
        self,
        database_path: str | Path,
        mappings: tuple[SQLTableMapping, ...],
    ) -> None:
        self.database_path = Path(database_path).resolve()
        self.mappings = mappings

    async def query(self, request: ProviderQuery) -> ProviderResult:
        results = await asyncio.to_thread(self._search, request.text, request.limit)
        return ProviderResult(
            provider_id=self.descriptor.id,
            data={"tables": results},
            sources=[
                SourceReference(
                    provider="sql",
                    title=f"Read-only SQLite: {self.database_path.name}",
                )
            ],
        )

    def _search(self, query: str, limit: int) -> dict[str, list[dict[str, Any]]]:
        if not self.database_path.is_file():
            raise FileNotFoundError(f"SQLite database not found: {self.database_path}")
        uri = self.database_path.as_uri() + "?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        connection.row_factory = sqlite3.Row
        try:
            results: dict[str, list[dict[str, Any]]] = {}
            remaining = limit
            for mapping in self.mappings:
                if remaining <= 0:
                    break
                output = ", ".join(_quoted(item) for item in mapping.output_columns)
                predicates = " OR ".join(
                    f"lower(CAST({_quoted(item)} AS TEXT)) LIKE ?"
                    for item in mapping.search_columns
                )
                # Identifiers have passed the strict regex and are quoted;
                # all caller-provided values remain bound parameters.
                statement = (
                    f"SELECT {output} FROM {_quoted(mapping.table)} "  # nosec B608
                    f"WHERE {predicates} LIMIT ?"
                )
                term = f"%{query.casefold()}%"
                parameters = (*([term] * len(mapping.search_columns)), remaining)
                rows = connection.execute(statement, parameters).fetchall()
                results[mapping.table] = [dict(row) for row in rows]
                remaining -= len(rows)
            return results
        finally:
            connection.close()


def mappings_from_settings(raw: list[dict[str, Any]]) -> tuple[SQLTableMapping, ...]:
    """Validate environment-supplied mappings before opening the database."""

    return tuple(SQLTableMapping.model_validate(item) for item in raw)


def _validated_identifier(value: str) -> str:
    if not IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(f"Unsafe SQL identifier: {value!r}")
    return value


def _quoted(identifier: str) -> str:
    return f'"{_validated_identifier(identifier)}"'
