"""Concurrent orchestration for the single pharmaceutical query entry point."""

from __future__ import annotations

import asyncio

from pharmacy_mcp.config import settings
from pharmacy_mcp.domain.models.provider import (
    KnowledgeProvider,
    ProviderQuery,
    ProviderResult,
    QueryCapability,
)
from pharmacy_mcp.domain.models.response import (
    ErrorDetail,
    ResponseStatus,
    ServiceResult,
    SourceReference,
)
from pharmacy_mcp.infrastructure.providers.registry import ProviderRegistry


class UnifiedQueryService:
    """Fan one query out to heterogeneous sources and preserve partial results."""

    def __init__(
        self,
        registry: ProviderRegistry,
        *,
        provider_timeout: float | None = None,
        max_parallel: int | None = None,
        max_providers: int | None = None,
    ) -> None:
        self.registry = registry
        self.provider_timeout = (
            settings.provider_timeout_seconds
            if provider_timeout is None
            else provider_timeout
        )
        self.max_parallel = (
            settings.provider_max_parallel if max_parallel is None else max_parallel
        )
        self.max_providers = (
            settings.provider_max_per_query if max_providers is None else max_providers
        )
        if self.provider_timeout <= 0:
            raise ValueError("provider_timeout must be greater than zero")
        if self.max_parallel <= 0:
            raise ValueError("max_parallel must be greater than zero")
        if self.max_providers <= 0:
            raise ValueError("max_providers must be greater than zero")

    async def query(
        self,
        *,
        text: str,
        capabilities: list[str] | None = None,
        sources: list[str] | None = None,
        limit: int = 10,
        context: dict[str, object] | None = None,
    ) -> ServiceResult:
        """Execute providers concurrently with isolated timeout/error handling."""

        requested_capabilities = tuple(
            QueryCapability(value)
            for value in (capabilities or [QueryCapability.SEARCH.value])
        )
        request = ProviderQuery(
            text=text,
            capabilities=requested_capabilities,
            limit=limit,
            context=context or {},
        )
        providers, missing = self.registry.resolve(
            source_ids=sources,
            capabilities=requested_capabilities,
        )

        errors = [
            ErrorDetail(
                code="provider_unavailable",
                message=f"Provider '{provider_id}' is not configured or registered.",
                provider=provider_id,
            )
            for provider_id in missing
        ]
        execution = {
            "provider_count": len(providers),
            "max_parallel": self.max_parallel,
            "max_providers": self.max_providers,
            "provider_timeout_seconds": self.provider_timeout,
        }
        if len(providers) > self.max_providers:
            errors.append(
                ErrorDetail(
                    code="provider_budget_exceeded",
                    message=(
                        f"Query resolved {len(providers)} providers, exceeding the "
                        f"configured maximum of {self.max_providers}. Select fewer "
                        "sources or narrow the requested capabilities."
                    ),
                )
            )
            return ServiceResult(
                status=ResponseStatus.ERROR,
                data={
                    "query": text,
                    "capabilities": [item.value for item in requested_capabilities],
                    "providers_queried": [],
                    "providers_resolved": [
                        provider.descriptor.id for provider in providers
                    ],
                    "provider_results": {},
                    "execution": execution,
                },
                errors=errors,
            )

        semaphore = asyncio.Semaphore(self.max_parallel)
        results = await asyncio.gather(
            *(
                self._query_provider(provider, request, semaphore)
                for provider in providers
            )
        )
        provider_data: dict[str, object] = {}
        sources_out: list[SourceReference] = []
        warnings: list[str] = []
        saw_partial = False

        for result in results:
            if result.status is ResponseStatus.ERROR:
                errors.extend(result.errors)
                continue
            saw_partial = saw_partial or result.status is ResponseStatus.PARTIAL
            provider_data[result.provider_id] = result.data
            sources_out.extend(result.sources)
            warnings.extend(result.warnings)
            errors.extend(result.errors)

        if provider_data and (errors or saw_partial):
            status = ResponseStatus.PARTIAL
        elif errors:
            status = ResponseStatus.ERROR
        else:
            status = ResponseStatus.OK

        return ServiceResult(
            status=status,
            data={
                "query": text,
                "capabilities": [item.value for item in requested_capabilities],
                "providers_queried": [provider.descriptor.id for provider in providers],
                "provider_results": provider_data,
                "execution": execution,
            },
            sources=_deduplicate_sources(sources_out),
            warnings=warnings,
            errors=errors,
        )

    async def _query_provider(
        self,
        provider: KnowledgeProvider,
        request: ProviderQuery,
        semaphore: asyncio.Semaphore,
    ) -> ProviderResult:
        try:
            async with semaphore:
                return await asyncio.wait_for(
                    provider.query(request),
                    timeout=self.provider_timeout,
                )
        except TimeoutError:
            return ProviderResult(
                provider_id=provider.descriptor.id,
                status=ResponseStatus.ERROR,
                data=None,
                errors=[
                    ErrorDetail(
                        code="provider_timeout",
                        message=(
                            f"Provider exceeded the {self.provider_timeout:g}s timeout."
                        ),
                        provider=provider.descriptor.id,
                        retryable=True,
                    )
                ],
            )
        except Exception as exc:
            return ProviderResult(
                provider_id=provider.descriptor.id,
                status=ResponseStatus.ERROR,
                data=None,
                errors=[
                    ErrorDetail(
                        code="provider_error",
                        message=str(exc),
                        provider=provider.descriptor.id,
                        retryable=True,
                    )
                ],
            )


def _deduplicate_sources(sources: list[SourceReference]) -> list[SourceReference]:
    unique: dict[tuple[str, str | None], SourceReference] = {}
    for source in sources:
        unique[(source.provider, source.uri)] = source
    return list(unique.values())
