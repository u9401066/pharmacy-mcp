"""Adapters that expose existing services through the provider port."""

from __future__ import annotations

import asyncio
from typing import Any

from pharmacy_mcp.application.services.taiwan_drug import TaiwanDrugService
from pharmacy_mcp.domain.models.provider import ProviderQuery, ProviderResult
from pharmacy_mcp.domain.models.response import ResponseStatus, SourceReference
from pharmacy_mcp.infrastructure.api.fda import FDAClient
from pharmacy_mcp.infrastructure.api.rxnorm import RxNormClient
from pharmacy_mcp.infrastructure.knowledge.formulary import FormularyKnowledge
from pharmacy_mcp.infrastructure.providers.catalog import get_provider_descriptor


class RxNormKnowledgeProvider:
    """RxNorm concept and class lookup."""

    descriptor = get_provider_descriptor("rxnorm")

    def __init__(self, client: RxNormClient | None = None) -> None:
        self.client = client or RxNormClient()

    async def query(self, request: ProviderQuery) -> ProviderResult:
        concepts = await self.client.search_by_name(request.text, request.limit)
        data = [
            {
                "rxcui": concept.rxcui,
                "name": concept.name,
                "synonym": concept.synonym,
                "term_type": concept.tty,
            }
            for concept in concepts
        ]
        return ProviderResult(
            provider_id=self.descriptor.id,
            data=data,
            sources=[_source(self.descriptor.id)],
        )


class OpenFDAKnowledgeProvider:
    """openFDA label search with a bounded agent-facing projection."""

    descriptor = get_provider_descriptor("openfda")

    def __init__(self, client: FDAClient | None = None) -> None:
        self.client = client or FDAClient()

    async def query(self, request: ProviderQuery) -> ProviderResult:
        labels = await self.client.search_drug_labels(request.text, request.limit)
        data = [
            {
                "brand_name": label.get("openfda", {}).get("brand_name", []),
                "generic_name": label.get("openfda", {}).get("generic_name", []),
                "manufacturer": label.get("openfda", {}).get(
                    "manufacturer_name", []
                ),
                "route": label.get("openfda", {}).get("route", []),
                "indications_and_usage": label.get("indications_and_usage", []),
                "warnings": label.get("warnings_and_cautions", []),
            }
            for label in labels
        ]
        return ProviderResult(
            provider_id=self.descriptor.id,
            data=data,
            sources=[_source(self.descriptor.id)],
        )


class TaiwanKnowledgeProvider:
    """Compound TFDA permit and NHI reimbursement lookup."""

    descriptor = get_provider_descriptor("tw-tfda")

    def __init__(self, service: TaiwanDrugService | None = None) -> None:
        self.service = service or TaiwanDrugService()

    async def query(self, request: ProviderQuery) -> ProviderResult:
        results: tuple[
            dict[str, Any] | BaseException,
            dict[str, Any] | BaseException,
        ] = await asyncio.gather(
            self.service.search_tfda_drug(request.text, limit=request.limit),
            self.service.get_nhi_coverage(request.text),
            return_exceptions=True,
        )
        tfda_result, nhi_result = results
        warnings: list[str] = []
        data: dict[str, object] = {}
        if isinstance(tfda_result, BaseException):
            warnings.append(f"TFDA query unavailable: {tfda_result}")
        else:
            data["tfda"] = tfda_result
        if isinstance(nhi_result, BaseException):
            warnings.append(f"NHI query unavailable: {nhi_result}")
        else:
            data["nhi"] = nhi_result

        return ProviderResult(
            provider_id="taiwan",
            status=ResponseStatus.PARTIAL if warnings else ResponseStatus.OK,
            data=data,
            sources=[_source("tw-tfda"), _source("tw-nhi")],
            warnings=warnings,
        )


class FormularyKnowledgeProvider:
    """Local hospital-formulary adapter."""

    descriptor = get_provider_descriptor("local-formulary")

    def __init__(self, formulary: FormularyKnowledge | None = None) -> None:
        self.formulary = formulary or FormularyKnowledge()

    async def query(self, request: ProviderQuery) -> ProviderResult:
        items = self.formulary.search(request.text, request.limit)
        return ProviderResult(
            provider_id=self.descriptor.id,
            data=[item.to_dict() for item in items],
            sources=[_source(self.descriptor.id)],
        )


def _source(provider_id: str) -> SourceReference:
    descriptor = get_provider_descriptor(provider_id)
    return SourceReference(
        provider=descriptor.id,
        title=descriptor.title,
        uri=descriptor.documentation_url,
    )
