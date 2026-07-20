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
from pharmacy_mcp.domain.models.response import (
    ErrorDetail,
    ResponseStatus,
    SourceReference,
)
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
        concepts = await self.client.search_by_name(
            request.text, min(request.limit, 20)
        )
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


class RxClassKnowledgeProvider:
    """Resolve RxNorm concepts and retrieve their real RxClass memberships."""

    descriptor = get_provider_descriptor("rxclass")

    def __init__(self, client: RxNormClient | None = None) -> None:
        self.client = client or RxNormClient()

    async def query(self, request: ProviderQuery) -> ProviderResult:
        concepts = await self.client.search_by_name(request.text, request.limit)
        class_results = await asyncio.gather(
            *(
                self.client.get_drug_class_memberships(concept.rxcui)
                for concept in concepts
            ),
            return_exceptions=True,
        )
        data: list[dict[str, object]] = []
        warnings: list[str] = []
        for concept, classes in zip(concepts, class_results, strict=True):
            if isinstance(classes, BaseException):
                warnings.append(f"RxClass lookup failed for RxCUI {concept.rxcui}")
                normalized_classes: list[dict[str, str | None]] = []
            else:
                normalized_classes = classes[:50]
            data.append(
                {
                    "rxcui": concept.rxcui,
                    "name": concept.name,
                    "term_type": concept.tty,
                    "classes": normalized_classes,
                }
            )

        return ProviderResult(
            provider_id=self.descriptor.id,
            status=ResponseStatus.PARTIAL if warnings else ResponseStatus.OK,
            data=data,
            sources=[_source(self.descriptor.id)],
            warnings=warnings,
        )


class OpenFDAKnowledgeProvider:
    """Capability-routed openFDA drug endpoints with bounded projections."""

    descriptor = get_provider_descriptor("openfda")

    def __init__(self, client: FDAClient | None = None) -> None:
        self.client = client or FDAClient()

    async def query(self, request: ProviderQuery) -> ProviderResult:
        requested = set(request.capabilities)
        jobs: list[tuple[str, Awaitable[list[dict[str, Any]]]]] = []
        label_capabilities = {
            QueryCapability.SEARCH,
            QueryCapability.LABEL,
            QueryCapability.DOSING,
            QueryCapability.SAFETY,
            QueryCapability.INTERACTION,
        }
        if requested.intersection(label_capabilities):
            jobs.append(
                (
                    "labels",
                    self.client.search_drug_labels(request.text, request.limit),
                )
            )
        if QueryCapability.ADVERSE_EVENT in requested:
            jobs.append(
                (
                    "adverse_events",
                    self.client.get_adverse_events(request.text, request.limit),
                )
            )
        if QueryCapability.NDC in requested:
            jobs.append(("ndc", self.client.search_ndc(request.text, request.limit)))
        if QueryCapability.RECALL in requested:
            jobs.append(
                ("recalls", self.client.search_recalls(request.text, request.limit))
            )
        if QueryCapability.APPROVAL in requested:
            jobs.append(
                (
                    "approvals",
                    self.client.search_approvals(request.text, request.limit),
                )
            )
        if QueryCapability.SHORTAGE in requested:
            jobs.append(
                (
                    "shortages",
                    self.client.search_shortages(request.text, request.limit),
                )
            )

        results = await asyncio.gather(
            *(job for _, job in jobs),
            return_exceptions=True,
        )
        data: dict[str, object] = {}
        warnings: list[str] = []
        errors: list[ErrorDetail] = []
        sources: list[SourceReference] = []
        for (name, _), result in zip(jobs, results, strict=True):
            if isinstance(result, BaseException):
                warnings.append(f"openFDA {name} endpoint failed")
                errors.append(
                    ErrorDetail(
                        code="openfda_endpoint_error",
                        message=f"The openFDA {name} endpoint was unavailable.",
                        provider=self.descriptor.id,
                        retryable=True,
                    )
                )
                continue
            data[name] = _project_openfda(name, result)
            sources.append(
                SourceReference(
                    provider=self.descriptor.id,
                    title=f"openFDA drug {name}",
                    uri=f"{self.client.base_url}/drug/{_OPENFDA_ENDPOINTS[name]}.json",
                )
            )

        if not jobs:
            warnings.append("No openFDA capability matched this query")
        successful = len(data)
        if errors and not successful:
            status = ResponseStatus.ERROR
        elif errors or warnings:
            status = ResponseStatus.PARTIAL
        else:
            status = ResponseStatus.OK
        return ProviderResult(
            provider_id=self.descriptor.id,
            status=status,
            data=data,
            sources=sources or [_source(self.descriptor.id)],
            warnings=warnings,
            errors=errors,
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


_OPENFDA_ENDPOINTS = {
    "labels": "label",
    "adverse_events": "event",
    "ndc": "ndc",
    "recalls": "enforcement",
    "approvals": "drugsfda",
    "shortages": "shortages",
}


def _project_openfda(name: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    projectors = {
        "labels": _project_label,
        "adverse_events": _project_adverse_event,
        "ndc": _project_ndc,
        "recalls": _project_recall,
        "approvals": _project_approval,
        "shortages": _project_shortage,
    }
    return [projectors[name](record) for record in records]


def _openfda(record: dict[str, Any], field: str) -> object:
    values = record.get("openfda", {})
    value = values.get(field, []) if isinstance(values, dict) else []
    return _bounded_values(value, max_items=20, max_chars=500)


def _project_label(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "brand_name": _openfda(record, "brand_name"),
        "generic_name": _openfda(record, "generic_name"),
        "manufacturer": _openfda(record, "manufacturer_name"),
        "route": _openfda(record, "route"),
        "indications_and_usage": _bounded_values(record.get("indications_and_usage")),
        "dosage_and_administration": _bounded_values(
            record.get("dosage_and_administration")
        ),
        "contraindications": _bounded_values(record.get("contraindications")),
        "warnings": _bounded_values(
            record.get("warnings_and_cautions", record.get("warnings", []))
        ),
        "adverse_reactions": _bounded_values(record.get("adverse_reactions")),
        "drug_interactions": _bounded_values(record.get("drug_interactions")),
    }


def _project_adverse_event(record: dict[str, Any]) -> dict[str, Any]:
    patient = record.get("patient", {})
    patient = patient if isinstance(patient, dict) else {}
    reactions = patient.get("reaction", [])
    drugs = patient.get("drug", [])
    reactions = reactions if isinstance(reactions, list) else []
    drugs = drugs if isinstance(drugs, list) else []
    return {
        "safety_report_id": record.get("safetyreportid"),
        "receipt_date": record.get("receiptdate"),
        "serious": record.get("serious"),
        "reactions": [
            item.get("reactionmeddrapt")
            for item in reactions[:20]
            if isinstance(item, dict) and item.get("reactionmeddrapt")
        ],
        "medicinal_products": [
            item.get("medicinalproduct")
            for item in drugs[:20]
            if isinstance(item, dict) and item.get("medicinalproduct")
        ],
    }


def _project_ndc(record: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "product_ndc",
        "generic_name",
        "brand_name",
        "labeler_name",
        "dosage_form",
        "route",
        "active_ingredients",
        "marketing_category",
        "marketing_start_date",
        "marketing_end_date",
        "listing_expiration_date",
    )
    projected = {field: record.get(field) for field in fields}
    projected["active_ingredients"] = _bounded_records(
        record.get("active_ingredients"),
        fields=("name", "strength"),
        max_items=20,
    )
    return projected


def _project_recall(record: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "recall_number",
        "status",
        "classification",
        "product_description",
        "reason_for_recall",
        "recalling_firm",
        "report_date",
        "distribution_pattern",
    )
    return {field: record.get(field) for field in fields}


def _project_approval(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "application_number": record.get("application_number"),
        "sponsor_name": record.get("sponsor_name"),
        "products": _bounded_records(
            record.get("products"),
            fields=(
                "product_number",
                "brand_name",
                "dosage_form",
                "route",
                "marketing_status",
                "reference_drug",
                "reference_standard",
                "te_code",
                "active_ingredients",
            ),
        ),
        "submissions": _bounded_records(
            record.get("submissions"),
            fields=(
                "submission_type",
                "submission_number",
                "submission_status",
                "submission_status_date",
                "review_priority",
                "submission_class_code",
                "submission_class_code_description",
            ),
        ),
        "brand_name": _openfda(record, "brand_name"),
        "generic_name": _openfda(record, "generic_name"),
    }


def _project_shortage(record: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "package_ndc",
        "generic_name",
        "proprietary_name",
        "company_name",
        "presentation",
        "availability",
        "shortage_reason",
        "therapeutic_category",
        "dosage_form",
        "strength",
        "status",
        "update_date",
        "initial_posting_date",
        "related_info",
        "related_info_link",
    )
    projected = {field: record.get(field) for field in fields}
    for field in ("strength", "therapeutic_category"):
        projected[field] = _bounded_values(
            projected[field], max_items=20, max_chars=500
        )
    return projected


def _bounded_values(
    value: object,
    *,
    max_items: int = 3,
    max_chars: int = 4_000,
) -> list[object]:
    values = value if isinstance(value, list) else []
    return [
        item[:max_chars] if isinstance(item, str) else item
        for item in values[:max_items]
    ]


def _bounded_records(
    value: object,
    *,
    fields: tuple[str, ...],
    max_items: int = 10,
) -> list[dict[str, object]]:
    values = value if isinstance(value, list) else []
    return [
        {field: item.get(field) for field in fields}
        for item in values[:max_items]
        if isinstance(item, dict)
    ]
