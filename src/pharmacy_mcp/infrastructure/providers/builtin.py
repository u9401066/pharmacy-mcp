"""Adapters that expose existing services through the provider port."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Any

from pharmacy_mcp.application.services.taiwan_drug import TaiwanDrugService
from pharmacy_mcp.domain.models.provider import (
    ProviderQuery,
    ProviderResult,
    QueryCapability,
)
from pharmacy_mcp.domain.models.response import ResponseStatus, SourceReference
from pharmacy_mcp.infrastructure.api.dailymed import DailyMedClient
from pharmacy_mcp.infrastructure.api.fda import FDAClient
from pharmacy_mcp.infrastructure.api.fhir import FHIRClient, FHIRSearchBatch
from pharmacy_mcp.infrastructure.api.medlineplus import MedlinePlusClient
from pharmacy_mcp.infrastructure.api.pubchem import PubChemClient
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
                "manufacturer": label.get("openfda", {}).get("manufacturer_name", []),
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


class DailyMedKnowledgeProvider:
    """DailyMed current Structured Product Label search."""

    descriptor = get_provider_descriptor("dailymed")

    def __init__(self, client: DailyMedClient | None = None) -> None:
        self.client = client or DailyMedClient()

    async def query(self, request: ProviderQuery) -> ProviderResult:
        data = await self.client.search_spls(request.text, request.limit)
        return ProviderResult(
            provider_id=self.descriptor.id,
            data=data,
            sources=[_source(self.descriptor.id)],
        )


class PubChemKnowledgeProvider:
    """PubChem chemical identity and calculated-property lookup."""

    descriptor = get_provider_descriptor("pubchem")

    def __init__(self, client: PubChemClient | None = None) -> None:
        self.client = client or PubChemClient()

    async def query(self, request: ProviderQuery) -> ProviderResult:
        data = await self.client.get_compound_by_name(request.text)
        return ProviderResult(
            provider_id=self.descriptor.id,
            data=data,
            sources=[_source(self.descriptor.id)],
        )


class MedlinePlusKnowledgeProvider:
    """MedlinePlus patient-education lookup by English medication name."""

    descriptor = get_provider_descriptor("medlineplus-connect")

    def __init__(self, client: MedlinePlusClient | None = None) -> None:
        self.client = client or MedlinePlusClient()

    async def query(self, request: ProviderQuery) -> ProviderResult:
        data = await self.client.search_medication(drug_name=request.text)
        return ProviderResult(
            provider_id=self.descriptor.id,
            data=data[: request.limit],
            sources=[_source(self.descriptor.id)],
        )


class FHIRKnowledgeProvider:
    """Hospital medication, formulary, patient-order, and inventory adapter."""

    descriptor = get_provider_descriptor("fhir")

    def __init__(self, client: FHIRClient | None = None) -> None:
        self.client = client or FHIRClient()

    async def query(self, request: ProviderQuery) -> ProviderResult:
        requested = set(request.capabilities)
        jobs: list[tuple[str, Awaitable[FHIRSearchBatch]]] = []
        if requested.intersection(
            {
                QueryCapability.SEARCH,
                QueryCapability.IDENTITY,
                QueryCapability.FORMULARY,
            }
        ):
            jobs.append(
                (
                    "medications",
                    self.client.search_medications(request.text, request.limit),
                )
            )
        if QueryCapability.INVENTORY in requested:
            jobs.append(
                ("inventory", self.client.search_inventory(request.text, request.limit))
            )

        patient_id = request.context.get("patient_id")
        if isinstance(patient_id, str) and patient_id:
            jobs.append(
                (
                    "patient_medications",
                    self.client.search_patient_medications(patient_id, request.limit),
                )
            )

        data: dict[str, object] = {
            "fhir_version": self.client.fhir_version,
            "server": self.client.base_url,
        }
        warnings: list[str] = []
        if jobs:
            results = await asyncio.gather(
                *(job for _, job in jobs),
                return_exceptions=True,
            )
            for (name, _), result in zip(jobs, results, strict=True):
                if isinstance(result, BaseException):
                    warnings.append(f"{name} query failed: {result}")
                    continue
                batch = result
                if not isinstance(batch, FHIRSearchBatch):
                    warnings.append(f"{name} returned an invalid adapter result")
                    continue
                data[name] = batch.resources
                warnings.extend(batch.warnings)
        else:
            warnings.append("No FHIR capability matched this query")

        return ProviderResult(
            provider_id=self.descriptor.id,
            status=ResponseStatus.PARTIAL if warnings else ResponseStatus.OK,
            data=data,
            sources=[
                SourceReference(
                    provider="fhir",
                    title="Configured hospital FHIR server",
                    uri=self.client.base_url,
                    version=self.client.fhir_version,
                )
            ],
            warnings=warnings,
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
            dict[str, Any] | BaseException,
        ] = await asyncio.gather(
            self.service.search_tfda_drug(request.text, limit=request.limit),
            self.service.search_nhi_drugs(request.text, limit=request.limit),
            self.service.get_nhi_coverage(request.text),
            return_exceptions=True,
        )
        tfda_result, nhi_items_result, nhi_coverage_result = results
        warnings: list[str] = []
        data: dict[str, object] = {}
        if isinstance(tfda_result, BaseException):
            warnings.append(f"TFDA query unavailable: {tfda_result}")
        else:
            data["tfda"] = tfda_result
        nhi: dict[str, object] = {}
        if isinstance(nhi_items_result, BaseException):
            warnings.append(f"NHI item query unavailable: {nhi_items_result}")
        else:
            nhi["items"] = nhi_items_result
        if isinstance(nhi_coverage_result, BaseException):
            warnings.append(f"NHI coverage query unavailable: {nhi_coverage_result}")
        else:
            nhi["coverage"] = nhi_coverage_result
        if nhi:
            data["nhi"] = nhi

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
