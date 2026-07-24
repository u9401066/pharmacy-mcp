"""Programmatic agent harness for the unified pharmacy knowledge gateway."""

from __future__ import annotations

from pharmacy_mcp.application.services.unified_query import UnifiedQueryService
from pharmacy_mcp.config import settings
from pharmacy_mcp.domain.models.response import OutputFormat, QueryResponse
from pharmacy_mcp.infrastructure.providers.registry import (
    ProviderRegistry,
    build_default_registry,
)

AGENT_CONTRACT_NAME = "pharmacy-query-contract"


def build_agent_contract(
    output_format: OutputFormat = OutputFormat.JSON,
    locale: str = "zh-TW",
) -> str:
    """Return deterministic instructions for an agent consuming this gateway."""

    return f"""You are using Pharmacy MCP as the single entry point for medication knowledge.

1. Call `query_pharmacy` for cross-source medication questions. Select explicit
   capabilities and sources when the task requires them.
2. Treat MCP `structuredContent` as authoritative. It must validate as
   `QueryResponse` schema version 1.0.
3. Preserve these top-level fields exactly when forwarding a result:
   `schema_version`, `status`, `data`, `sources`, `warnings`, `errors`, `meta`.
4. Do not invent, complete, reconcile, or silently discard missing clinical
   facts. Keep each provider payload and provenance distinct. Surface partial
   failures, warnings, and the medical disclaimer.
5. Never place credentials in tool arguments. Include patient identifiers only
   when an authorized workflow explicitly requires a patient-scoped FHIR query.
6. Request `output_format={output_format.value}` and `locale={locale}`. For JSON
   formats, emit only the validated response object with no prose or code fence.
   For Markdown, reproduce the gateway rendering without changing its meaning.
"""


class PharmacyHarness:
    """Transport-neutral single entry point for Python agents and workflows."""

    def __init__(
        self,
        registry: ProviderRegistry | None = None,
        *,
        provider_timeout: float | None = None,
    ) -> None:
        self.registry = registry or build_default_registry()
        self.service = UnifiedQueryService(
            self.registry,
            provider_timeout=provider_timeout,
        )

    async def query(
        self,
        text: str,
        *,
        capabilities: list[str] | None = None,
        sources: list[str] | None = None,
        limit: int = 10,
        context: dict[str, object] | None = None,
        output_format: OutputFormat | str | None = None,
        locale: str | None = None,
    ) -> QueryResponse:
        """Run a compound query and return a validated response object."""

        selected_format = OutputFormat(output_format or settings.default_output_format)
        selected_locale = locale or settings.default_locale
        result = await self.service.query(
            text=text,
            capabilities=capabilities,
            sources=sources,
            limit=limit,
            context=context,
        )
        return QueryResponse.from_service(
            tool="query_pharmacy",
            result=result,
            output_format=selected_format,
            locale=selected_locale,
            disclaimer=settings.disclaimer,
        )

    def render(self, response: QueryResponse) -> str:
        """Render the response according to its validated metadata."""

        from pharmacy_mcp.presentation.formatting import ResponseFormatter

        return ResponseFormatter.render(response, response.meta.output_format)

    def agent_contract(
        self,
        output_format: OutputFormat | str | None = None,
        locale: str | None = None,
    ) -> str:
        """Return the exact consumption and forwarding rules for an agent."""

        return build_agent_contract(
            OutputFormat(output_format or settings.default_output_format),
            locale or settings.default_locale,
        )
