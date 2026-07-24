"""Versioned response envelope used to constrain agent-facing output."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION: Literal["1.0"] = "1.0"


class OutputFormat(StrEnum):
    """Supported human-readable renderings of structured MCP results."""

    JSON = "json"
    JSON_COMPACT = "json_compact"
    MARKDOWN = "markdown"


class ResponseStatus(StrEnum):
    """Outcome of a query across one or more providers."""

    OK = "ok"
    PARTIAL = "partial"
    ERROR = "error"


class SourceReference(BaseModel):
    """Traceable provenance for one result source."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(description="Stable provider identifier")
    title: str = Field(description="Human-readable source name")
    uri: str | None = Field(default=None, description="Source or query URI")
    retrieved_at: str | None = Field(
        default=None,
        description="ISO-8601 retrieval time when data was fetched",
    )
    version: str | None = Field(default=None, description="Dataset/API version")


class ErrorDetail(BaseModel):
    """Machine-actionable error without exposing internal stack traces."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    provider: str | None = None
    retryable: bool = False


class ResponseMeta(BaseModel):
    """Metadata that is stable across all tools and transports."""

    model_config = ConfigDict(extra="forbid")

    tool: str
    output_format: OutputFormat
    locale: str
    result_count: int | None = None
    disclaimer: str


class QueryResponse(BaseModel):
    """Canonical MCP response envelope.

    Agents MUST consume ``data`` and preserve the other fields when forwarding a
    result. Unknown top-level fields are rejected so accidental format drift is
    detected by the MCP SDK's output-schema validation.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    status: ResponseStatus
    data: Any
    sources: list[SourceReference]
    warnings: list[str]
    errors: list[ErrorDetail]
    meta: ResponseMeta

    @classmethod
    def success(
        cls,
        *,
        tool: str,
        data: Any,
        output_format: OutputFormat,
        locale: str,
        disclaimer: str,
        sources: list[SourceReference] | None = None,
        warnings: list[str] | None = None,
        partial: bool = False,
    ) -> QueryResponse:
        """Build a validated successful or partial response."""

        return cls(
            schema_version=SCHEMA_VERSION,
            status=ResponseStatus.PARTIAL if partial else ResponseStatus.OK,
            data=data,
            sources=sources or [],
            warnings=warnings or [],
            errors=[],
            meta=ResponseMeta(
                tool=tool,
                output_format=output_format,
                locale=locale,
                result_count=_infer_result_count(data),
                disclaimer=disclaimer,
            ),
        )

    @classmethod
    def failure(
        cls,
        *,
        tool: str,
        code: str,
        message: str,
        output_format: OutputFormat,
        locale: str,
        disclaimer: str,
        retryable: bool = False,
    ) -> QueryResponse:
        """Build a validated error response."""

        return cls(
            schema_version=SCHEMA_VERSION,
            status=ResponseStatus.ERROR,
            data=None,
            sources=[],
            warnings=[],
            errors=[
                ErrorDetail(
                    code=code,
                    message=message,
                    retryable=retryable,
                )
            ],
            meta=ResponseMeta(
                tool=tool,
                output_format=output_format,
                locale=locale,
                disclaimer=disclaimer,
            ),
        )

    @classmethod
    def from_service(
        cls,
        *,
        tool: str,
        result: ServiceResult,
        output_format: OutputFormat,
        locale: str,
        disclaimer: str,
    ) -> QueryResponse:
        """Wrap an application result without discarding partial-failure details."""

        return cls(
            schema_version=SCHEMA_VERSION,
            status=result.status,
            data=result.data,
            sources=result.sources,
            warnings=result.warnings,
            errors=result.errors,
            meta=ResponseMeta(
                tool=tool,
                output_format=output_format,
                locale=locale,
                result_count=_infer_result_count(result.data),
                disclaimer=disclaimer,
            ),
        )


class ServiceResult(BaseModel):
    """Transport-neutral result returned by composite application services."""

    model_config = ConfigDict(extra="forbid")

    status: ResponseStatus
    data: Any
    sources: list[SourceReference] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[ErrorDetail] = Field(default_factory=list)


def _infer_result_count(data: Any) -> int | None:
    """Infer a useful result count without changing provider payloads."""

    if isinstance(data, list):
        return len(data)
    if not isinstance(data, dict):
        return None

    for key in ("result_count", "total_count", "count"):
        value = data.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value

    for key in ("results", "items"):
        value = data.get(key)
        if isinstance(value, list):
            return len(value)
    return None
