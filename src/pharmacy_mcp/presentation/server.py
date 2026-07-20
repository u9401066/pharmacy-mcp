"""MCP Server entry point and deployment helpers."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from functools import lru_cache
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent, Tool
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.types import Receive, Scope, Send

from pharmacy_mcp.application.harness import AGENT_CONTRACT_NAME, build_agent_contract
from pharmacy_mcp.application.services.dosage import DosageService
from pharmacy_mcp.application.services.drug_info import DrugInfoService
from pharmacy_mcp.application.services.drug_search import DrugSearchService
from pharmacy_mcp.application.services.interaction import InteractionService
from pharmacy_mcp.application.services.prescription import PrescriptionService
from pharmacy_mcp.application.services.simulation import SimulationService
from pharmacy_mcp.application.services.taiwan_drug import TaiwanDrugService
from pharmacy_mcp.application.services.unified_query import UnifiedQueryService
from pharmacy_mcp.config import settings
from pharmacy_mcp.domain.models.provider import QueryCapability
from pharmacy_mcp.domain.models.response import (
    OutputFormat,
    QueryResponse,
    ServiceResult,
)
from pharmacy_mcp.infrastructure.knowledge.formula_catalog import FormulaCatalog
from pharmacy_mcp.infrastructure.providers.catalog import PROVIDER_CATALOG
from pharmacy_mcp.infrastructure.providers.registry import (
    ProviderRegistry,
    build_default_registry,
)
from pharmacy_mcp.presentation.formatting import ResponseFormatter

logger = logging.getLogger(__name__)

SERVER_NAME = "pharmacy-mcp"
SERVER_INSTRUCTIONS = (
    "Use this server as the single pharmacy knowledge entry point. Every tool returns "
    "the versioned QueryResponse envelope in structuredContent. Preserve "
    "schema_version, status, sources, warnings, errors, and meta; never invent "
    "missing clinical facts. "
    f"Always include the project disclaimer: {settings.disclaimer}"
)
SERVER_WEBSITE_URL = "https://github.com/u9401066/pharmacy-mcp"

ToolResult = dict[str, Any]
OUTPUT_SCHEMA = QueryResponse.model_json_schema()
OUTPUT_FORMAT_PROPERTY: dict[str, Any] = {
    "type": "string",
    "enum": [item.value for item in OutputFormat],
    "default": settings.default_output_format,
    "description": (
        "Text rendering. structuredContent always follows the versioned outputSchema."
    ),
}
LOCALE_PROPERTY: dict[str, Any] = {
    "type": "string",
    "default": settings.default_locale,
    "description": "BCP 47 locale for labels and messages (for example zh-TW).",
}


class PharmacyFastMCP(FastMCP):
    """FastMCP server that enforces one response envelope for every tool."""

    async def list_tools(self) -> list[Tool]:
        """Expose shared rendering inputs and the canonical output schema."""

        return _decorate_tools(await super().list_tools())

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> Sequence[Any] | dict[str, Any]:
        """Run a tool and normalize success, partial, and error results."""

        output_format = _parse_output_format(arguments.get("output_format"))
        locale = str(arguments.get("locale", settings.default_locale))
        service_arguments = {
            key: value
            for key, value in arguments.items()
            if key not in {"output_format", "locale"}
        }
        try:
            converted = await super().call_tool(name, service_arguments)
            raw = _extract_structured_result(converted)
            if name == "query_pharmacy":
                response = QueryResponse.from_service(
                    tool=name,
                    result=ServiceResult.model_validate(raw),
                    output_format=output_format,
                    locale=locale,
                    disclaimer=settings.disclaimer,
                )
            elif isinstance(raw, dict) and raw.get("schema_version") == "1.0":
                response = QueryResponse.model_validate(raw)
            else:
                response = QueryResponse.success(
                    tool=name,
                    data=raw,
                    output_format=output_format,
                    locale=locale,
                    disclaimer=settings.disclaimer,
                )
            return _render_tool_response(response, output_format)
        except Exception as exc:
            logger.exception("Error in tool %s", name)
            response = QueryResponse.failure(
                tool=name,
                code="tool_execution_error",
                message=str(exc),
                output_format=output_format,
                locale=locale,
                disclaimer=settings.disclaimer,
            )
            return _render_tool_response(response, output_format)


@lru_cache(maxsize=1)
def get_drug_search_service() -> DrugSearchService:
    """Return the lazily initialized drug search service."""
    return DrugSearchService()


@lru_cache(maxsize=1)
def get_drug_info_service() -> DrugInfoService:
    """Return the lazily initialized drug information service."""
    return DrugInfoService()


@lru_cache(maxsize=1)
def get_formula_catalog() -> FormulaCatalog:
    """Return the lazily loaded trusted formula catalog."""
    return FormulaCatalog()


@lru_cache(maxsize=1)
def get_simulation_service() -> SimulationService:
    """Return the lazily initialized simulation service."""
    return SimulationService(formula_catalog=get_formula_catalog())


@lru_cache(maxsize=1)
def get_interaction_service() -> InteractionService:
    """Return the lazily initialized interaction service."""
    return InteractionService(simulation_service=get_simulation_service())


@lru_cache(maxsize=1)
def get_dosage_service() -> DosageService:
    """Return the lazily initialized dosage service."""
    return DosageService()


@lru_cache(maxsize=1)
def get_taiwan_drug_service() -> TaiwanDrugService:
    """Return the lazily initialized Taiwan drug service."""
    return TaiwanDrugService()


@lru_cache(maxsize=1)
def get_prescription_service() -> PrescriptionService:
    """Return the lazily initialized prescription service."""
    return PrescriptionService()


@lru_cache(maxsize=1)
def get_provider_registry() -> ProviderRegistry:
    """Return all enabled API, FHIR, database, file, vector, and web providers."""

    return build_default_registry()


@lru_cache(maxsize=1)
def get_unified_query_service() -> UnifiedQueryService:
    """Return the composite pharmacy knowledge query service."""

    return UnifiedQueryService(get_provider_registry())


def create_server(
    *,
    host: str | None = None,
    port: int | None = None,
    mount_path: str | None = None,
    streamable_http_path: str | None = None,
    stateless_http: bool | None = None,
) -> PharmacyFastMCP:
    """Create and configure the MCP server using FastMCP."""
    server = PharmacyFastMCP(
        name=SERVER_NAME,
        instructions=SERVER_INSTRUCTIONS,
        website_url=SERVER_WEBSITE_URL,
        host=settings.host if host is None else host,
        port=settings.port if port is None else port,
        mount_path=settings.mount_path if mount_path is None else mount_path,
        streamable_http_path=(
            settings.streamable_http_path
            if streamable_http_path is None
            else streamable_http_path
        ),
        stateless_http=(
            settings.stateless_http if stateless_http is None else stateless_http
        ),
        log_level="INFO",
    )

    @server.tool(
        description=(
            "Single pharmaceutical knowledge entry point. Query compatible public "
            "APIs, Taiwan NHI/TFDA, hospital FHIR inventory, SQL, files, vector "
            "search, and configured web sources concurrently."
        )
    )
    async def query_pharmacy(
        query: str,
        capabilities: list[str] | None = None,
        sources: list[str] | None = None,
        limit: int = 10,
        context: dict[str, Any] | None = None,
    ) -> ToolResult:
        result = await get_unified_query_service().query(
            text=query,
            capabilities=capabilities,
            sources=sources,
            limit=limit,
            context=context,
        )
        return result.model_dump(mode="json")

    @server.tool(
        description=(
            "List cataloged pharmacy knowledge sources, capabilities, readiness, "
            "credential requirements, and runtime registration state."
        )
    )
    def list_knowledge_sources(
        state: str | None = None,
        capability: str | None = None,
    ) -> ToolResult:
        catalog = get_provider_registry().catalog()
        if state:
            catalog = [item for item in catalog if item["state"] == state]
        if capability:
            catalog = [item for item in catalog if capability in item["capabilities"]]
        return {"count": len(catalog), "providers": catalog}

    @server.tool(
        description=(
            "Inspect the Taiwan NHI official index freshness, row count, local path, "
            "and upstream dataset URL without forcing a download."
        )
    )
    def get_nhi_data_status() -> ToolResult:
        return get_taiwan_drug_service().get_nhi_data_status()

    @server.tool(
        description="Search for drugs by name. Returns results from RxNorm and FDA databases."
    )
    async def search_drug(query: str, max_results: int = 10) -> ToolResult:
        return await _handle_legacy_tool(
            "search_drug",
            {"query": query, "max_results": max_results},
        )

    @server.tool(
        description=(
            "Get comprehensive information about a drug including indications, "
            "dosage, warnings, and pharmacology."
        )
    )
    async def get_drug_info(drug_name: str) -> ToolResult:
        return await _handle_legacy_tool("get_drug_info", {"drug_name": drug_name})

    @server.tool(description="Get dosage and administration information for a drug.")
    async def get_drug_dosage(drug_name: str) -> ToolResult:
        return await _handle_legacy_tool("get_drug_dosage", {"drug_name": drug_name})

    @server.tool(
        description="Get warnings, contraindications, and adverse reactions for a drug."
    )
    async def get_drug_warnings(drug_name: str) -> ToolResult:
        return await _handle_legacy_tool("get_drug_warnings", {"drug_name": drug_name})

    @server.tool(description="Check for interactions between two drugs.")
    async def check_drug_interaction(drug1: str, drug2: str) -> ToolResult:
        return await _handle_legacy_tool(
            "check_drug_interaction", {"drug1": drug1, "drug2": drug2}
        )

    @server.tool(
        description="Check for interactions among multiple drugs (medication list review)."
    )
    async def check_multi_drug_interactions(drugs: list[str]) -> ToolResult:
        return await _handle_legacy_tool(
            "check_multi_drug_interactions", {"drugs": drugs}
        )

    @server.tool(description="Check for food-drug interactions for a specific drug.")
    async def check_food_drug_interaction(drug_name: str) -> ToolResult:
        return await _handle_legacy_tool(
            "check_food_drug_interaction", {"drug_name": drug_name}
        )

    @server.tool(description="Calculate weight-based dosage (mg/kg).")
    def calculate_dose_by_weight(
        dose_per_kg: float,
        patient_weight_kg: float,
        dose_unit: str = "mg",
        max_dose: float | None = None,
    ) -> ToolResult:
        return get_dosage_service().calculate_weight_based_dose(
            dose_per_kg=dose_per_kg,
            patient_weight_kg=patient_weight_kg,
            dose_unit=dose_unit,
            max_dose=max_dose,
        )

    @server.tool(
        description="Calculate BSA-based dosage (mg/m²), commonly used in oncology."
    )
    def calculate_dose_by_bsa(
        dose_per_m2: float,
        height_cm: float,
        weight_kg: float,
        dose_unit: str = "mg",
        max_dose: float | None = None,
    ) -> ToolResult:
        return get_dosage_service().calculate_bsa_based_dose(
            dose_per_m2=dose_per_m2,
            height_cm=height_cm,
            weight_kg=weight_kg,
            dose_unit=dose_unit,
            max_dose=max_dose,
        )

    @server.tool(
        description=(
            "Calculate creatinine clearance using Cockcroft-Gault formula for renal "
            "dosing adjustments."
        )
    )
    def calculate_creatinine_clearance(
        age_years: int,
        weight_kg: float,
        serum_creatinine: float,
        gender: str,
    ) -> ToolResult:
        return get_dosage_service().calculate_creatinine_clearance(
            age_years=age_years,
            weight_kg=weight_kg,
            serum_creatinine=serum_creatinine,
            gender=gender,
        )

    @server.tool(
        description="Calculate pediatric dose from adult dose using weight, age, or BSA method."
    )
    def calculate_pediatric_dose(
        adult_dose: float,
        child_weight_kg: float,
        method: str = "weight",
        child_age_years: int | None = None,
        child_bsa: float | None = None,
        dose_unit: str = "mg",
    ) -> ToolResult:
        return get_dosage_service().calculate_pediatric_dose(
            adult_dose=adult_dose,
            child_weight_kg=child_weight_kg,
            dose_unit=dose_unit,
            method=method,
            child_age_years=child_age_years,
            child_bsa=child_bsa,
        )

    @server.tool(description="Calculate IV infusion rate.")
    def calculate_infusion_rate(
        total_dose: float,
        dose_unit: str,
        volume_ml: float,
        duration_hours: float,
    ) -> ToolResult:
        return get_dosage_service().calculate_infusion_rate(
            total_dose=total_dose,
            dose_unit=dose_unit,
            volume_ml=volume_ml,
            duration_hours=duration_hours,
        )

    @server.tool(description="Convert between dose units (g, mg, mcg, ng).")
    def convert_dose_units(value: float, from_unit: str, to_unit: str) -> ToolResult:
        return get_dosage_service().convert_dose_units(
            value=value,
            from_unit=from_unit,
            to_unit=to_unit,
        )

    @server.tool(
        description=(
            "Search the Taiwan TFDA drug database for permits and product information."
        )
    )
    async def search_tfda_drug(
        query: str,
        search_type: str = "name",
        limit: int = 20,
    ) -> ToolResult:
        return await _handle_legacy_tool(
            "search_tfda_drug",
            {"query": query, "search_type": search_type, "limit": limit},
        )

    @server.tool(
        description=(
            "Check whether a drug is covered by Taiwan National Health Insurance "
            "(NHI) and return coverage details."
        )
    )
    async def get_nhi_coverage(drug_name: str) -> ToolResult:
        return await _handle_legacy_tool("get_nhi_coverage", {"drug_name": drug_name})

    @server.tool(description="Get NHI reimbursement price for a drug by NHI code.")
    async def get_nhi_drug_price(nhi_code: str) -> ToolResult:
        return await _handle_legacy_tool("get_nhi_drug_price", {"nhi_code": nhi_code})

    @server.tool(
        description=(
            "Translate drug names between English and Traditional Chinese where "
            "local mapping data is available."
        )
    )
    async def translate_drug_name(name: str) -> ToolResult:
        return await _handle_legacy_tool("translate_drug_name", {"name": name})

    @server.tool(description="List drugs requiring NHI prior authorization.")
    async def list_prior_authorization_drugs() -> ToolResult:
        return await _handle_legacy_tool("list_prior_authorization_drugs", {})

    @server.tool(
        description="List all NHI coverage rules available in the local database."
    )
    async def list_nhi_coverage_rules() -> ToolResult:
        return get_taiwan_drug_service().list_nhi_coverage_rules()

    @server.tool(description="Get hospital formulary item details by drug code.")
    def get_formulary_item(drug_code: str) -> ToolResult:
        item = get_prescription_service().get_formulary_item(drug_code)
        if item:
            return item.to_dict()
        return {"error": f"Drug code {drug_code} not found in formulary"}

    @server.tool(description="Search hospital formulary by drug name or code.")
    def search_formulary(query: str, limit: int = 10) -> ToolResult:
        items = get_prescription_service().search_formulary(query=query, limit=limit)
        return {"count": len(items), "items": [item.to_dict() for item in items]}

    @server.tool(
        description=(
            "Get renal dosing adjustment recommendation based on creatinine "
            "clearance (CrCl)."
        )
    )
    def get_renal_adjustment(drug_code: str, crcl: float) -> ToolResult:
        adjustment = get_prescription_service().get_renal_adjustment(
            drug_code=drug_code, crcl=crcl
        )
        return adjustment.to_dict()

    @server.tool(description="Validate a medication order before submission.")
    def validate_order(
        drug_code: str,
        dose: float,
        dose_unit: str,
        route: str,
        frequency: str,
        patient_crcl: float | None = None,
    ) -> ToolResult:
        result = get_prescription_service().validate_order(
            drug_code=drug_code,
            dose=dose,
            dose_unit=dose_unit,
            route=route,
            frequency=frequency,
            patient_crcl=patient_crcl,
        )
        return result.to_dict()

    @server.tool(description="Submit a medication order to the HIS service.")
    async def submit_order(
        patient_id: str,
        drug_code: str,
        dose: float,
        dose_unit: str,
        route: str,
        frequency: str,
        duration_days: int,
        physician_id: str,
        override_warnings: bool = False,
        notes: str | None = None,
    ) -> ToolResult:
        result = await get_prescription_service().submit_order(
            patient_id=patient_id,
            drug_code=drug_code,
            dose=dose,
            dose_unit=dose_unit,
            route=route,
            frequency=frequency,
            duration_days=duration_days,
            physician_id=physician_id,
            override_warnings=override_warnings,
            notes=notes,
        )
        return result.to_dict()

    @server.tool(description="Discontinue an active medication order.")
    async def stop_order(order_id: str, reason: str) -> ToolResult:
        result = await get_prescription_service().stop_order(
            order_id=order_id, reason=reason
        )
        return result.to_dict()

    @server.tool(description="List trusted PK/DDI formulas available for simulation.")
    def list_formula_catalog(status: str | None = "trusted") -> ToolResult:
        return get_formula_catalog().to_dict(status=status)

    @server.tool(description="Get full metadata for a trusted PK/DDI formula.")
    def get_formula_details(formula_id: str) -> ToolResult:
        formula = get_formula_catalog().get_formula(formula_id)
        if formula is None:
            return {"error": f"Formula {formula_id} not found"}
        return formula.to_dict()

    @server.tool(
        description=(
            "Explain the supported mechanistic DDI pathway for a drug pair, "
            "including required simulation parameters."
        )
    )
    def explain_interaction_mechanism(drug1: str, drug2: str) -> ToolResult:
        return get_interaction_service().explain_interaction_mechanism(drug1, drug2)

    @server.tool(
        description=(
            "Run a PBPK-lite CYP reversible inhibition exposure estimate for a "
            "supported drug pair using explicit user-supplied parameters."
        )
    )
    def simulate_pk_interaction(
        drug1: str,
        drug2: str,
        cl_total: float,
        fm: float,
        inhibitor_concentration: float,
        ki: float,
    ) -> ToolResult:
        return get_interaction_service().simulate_pk_interaction(
            drug1=drug1,
            drug2=drug2,
            cl_total=cl_total,
            fm=fm,
            inhibitor_concentration=inhibitor_concentration,
            ki=ki,
        )

    @server.tool(description="Run a one-compartment concentration-time estimate.")
    def simulate_concentration_time(
        dose: float,
        vd: float,
        ke: float,
        time: float,
    ) -> ToolResult:
        return get_simulation_service().simulate_concentration_time(
            dose=dose,
            vd=vd,
            ke=ke,
            time=time,
        )

    @server.resource(
        "pharmacy://server/disclaimer",
        name="server_disclaimer",
        description="Pharmacy MCP medical disclaimer.",
        mime_type="text/plain",
    )
    def server_disclaimer() -> str:
        return settings.disclaimer

    @server.resource(
        "pharmacy://formulas",
        name="trusted_formula_catalog",
        description="Trusted PK/DDI formula catalog metadata.",
        mime_type="application/json",
    )
    def trusted_formula_catalog() -> ToolResult:
        return get_formula_catalog().to_dict()

    @server.resource(
        "pharmacy://formulas/{formula_id}",
        name="trusted_formula_details",
        description="Trusted PK/DDI formula metadata by formula ID.",
        mime_type="application/json",
    )
    def trusted_formula_details(formula_id: str) -> ToolResult:
        formula = get_formula_catalog().get_formula(formula_id)
        if formula is None:
            raise ValueError(f"Formula {formula_id} not found")
        return formula.to_dict()

    @server.resource(
        "pharmacy://validation/formulas",
        name="formula_validation_cases",
        description="Validation fixtures for trusted PK/DDI formulas.",
        mime_type="application/json",
    )
    def formula_validation_cases() -> ToolResult:
        return {
            "version": get_formula_catalog().version,
            "formulas": [
                {
                    "id": formula.id,
                    "validation_cases": list(formula.validation_cases),
                }
                for formula in get_formula_catalog().list_formulas()
            ],
        }

    @server.prompt(
        name="ddi_analysis_workflow",
        description="Prompt template for evidence-backed DDI analysis.",
    )
    def ddi_analysis_workflow(drug1: str, drug2: str) -> str:
        return (
            f"Analyze the potential interaction between {drug1} and {drug2}. "
            "First call explain_interaction_mechanism. If the mechanism is supported "
            "and explicit parameters are available, call simulate_pk_interaction. "
            "Report evidence, assumptions, limitations, and data gaps. "
            f"Always include this disclaimer: {settings.disclaimer}"
        )

    @server.prompt(
        name="formula_review_checklist",
        description="Prompt template for reviewing draft formulas before trust promotion.",
    )
    def formula_review_checklist(formula_id: str = "draft_formula") -> str:
        return (
            f"Review {formula_id} before adding it to the trusted catalog. Confirm "
            "the expression, parameter units, assumptions, limitations, source "
            "references, validation cases, fail-closed behavior, and whether the "
            "formula is only a screening approximation. Draft or external formulas "
            "must not be used for clinical decisions until committed and tested."
        )

    @server.prompt(
        name=AGENT_CONTRACT_NAME,
        description=(
            "Constrain an agent to the versioned Pharmacy MCP response envelope."
        ),
    )
    def pharmacy_query_contract(
        output_format: str = settings.default_output_format,
        locale: str = settings.default_locale,
    ) -> str:
        return build_agent_contract(_parse_output_format(output_format), locale)

    return server


def _decorate_tools(tools: list[Tool]) -> list[Tool]:
    """Apply the shared input/output contract to the complete tool catalog."""

    for tool in tools:
        properties = tool.inputSchema.setdefault("properties", {})
        properties["output_format"] = OUTPUT_FORMAT_PROPERTY.copy()
        properties["locale"] = LOCALE_PROPERTY.copy()
        if tool.name == "query_pharmacy":
            _set_array_item_enum(
                properties["capabilities"],
                [item.value for item in QueryCapability],
            )
            _set_array_item_enum(
                properties["sources"],
                [item.id for item in PROVIDER_CATALOG],
            )
        tool.outputSchema = OUTPUT_SCHEMA
        tool.description = (
            f"{tool.description or ''} "
            "Agent contract: use structuredContent as the source of truth; "
            "preserve schema_version/status/sources/warnings/errors/meta when "
            "forwarding the result and never infer missing clinical facts."
        ).strip()
    return tools


def _set_array_item_enum(schema: dict[str, Any], values: list[str]) -> None:
    """Add an enum to a direct or nullable Pydantic array schema."""

    array_schema = schema
    if "anyOf" in schema:
        array_schema = next(
            option for option in schema["anyOf"] if option.get("type") == "array"
        )
    array_schema.setdefault("items", {})["enum"] = values


def _parse_output_format(value: Any) -> OutputFormat:
    """Resolve a requested output format after input validation."""

    return OutputFormat(value or settings.default_output_format)


def _extract_structured_result(converted: Any) -> Any:
    """Extract FastMCP structured output before applying our canonical envelope."""

    if isinstance(converted, CallToolResult):
        if converted.structuredContent is not None:
            return converted.structuredContent
        return [block.model_dump(mode="json") for block in converted.content]
    if isinstance(converted, tuple) and len(converted) == 2:
        return converted[1]
    if isinstance(converted, dict):
        return converted
    if isinstance(converted, Sequence) and not isinstance(converted, (str, bytes)):
        return [
            block.model_dump(mode="json") if hasattr(block, "model_dump") else block
            for block in converted
        ]
    return converted


def _render_tool_response(
    response: QueryResponse,
    output_format: OutputFormat,
) -> tuple[list[TextContent], dict[str, Any]]:
    """Return deterministic text plus authoritative structured content."""

    return (
        [
            TextContent(
                type="text",
                text=ResponseFormatter.render(response, output_format),
            )
        ],
        response.model_dump(mode="json"),
    )


async def _handle_legacy_tool(
    name: str,
    arguments: dict[str, Any],
) -> ToolResult:
    """Route a legacy catalog tool while retaining a precise return type."""

    result = await _handle_tool(name, arguments)
    if isinstance(result, ServiceResult):
        raise TypeError(f"Unexpected composite result for legacy tool {name}")
    return result


async def _handle_tool(
    name: str,
    arguments: dict[str, Any],
) -> ToolResult | ServiceResult:
    """Route tool calls to appropriate service methods."""
    if name == "query_pharmacy":
        return await get_unified_query_service().query(
            text=arguments["query"],
            capabilities=arguments.get("capabilities"),
            sources=arguments.get("sources"),
            limit=arguments.get("limit", 10),
            context=arguments.get("context"),
        )

    if name == "list_knowledge_sources":
        catalog = get_provider_registry().catalog()
        state = arguments.get("state")
        capability = arguments.get("capability")
        if state:
            catalog = [item for item in catalog if item["state"] == state]
        if capability:
            catalog = [item for item in catalog if capability in item["capabilities"]]
        return {"count": len(catalog), "providers": catalog}

    if name == "get_nhi_data_status":
        return get_taiwan_drug_service().get_nhi_data_status()

    if name == "search_drug":
        return await get_drug_search_service().search(
            query=arguments["query"],
            max_results=arguments.get("max_results", 10),
        )

    if name == "get_drug_info":
        return await get_drug_info_service().get_full_info(arguments["drug_name"])

    if name == "get_drug_dosage":
        return await get_drug_info_service().get_dosage_info(arguments["drug_name"])

    if name == "get_drug_warnings":
        return await get_drug_info_service().get_warnings(arguments["drug_name"])

    if name == "check_drug_interaction":
        return await get_interaction_service().check_drug_drug_interaction(
            drug1=arguments["drug1"],
            drug2=arguments["drug2"],
        )

    if name == "check_multi_drug_interactions":
        return await get_interaction_service().check_multi_drug_interactions(
            arguments["drugs"]
        )

    if name == "check_food_drug_interaction":
        return await get_interaction_service().check_food_drug_interaction(
            arguments["drug_name"]
        )

    if name == "search_tfda_drug":
        return await get_taiwan_drug_service().search_tfda_drug(
            query=arguments["query"],
            limit=arguments.get("limit", 20),
            search_type=arguments.get("search_type", "name"),
        )

    if name == "get_nhi_coverage":
        return await get_taiwan_drug_service().get_nhi_coverage(arguments["drug_name"])

    if name == "get_nhi_drug_price":
        return await get_taiwan_drug_service().get_nhi_drug_price(arguments["nhi_code"])

    if name == "translate_drug_name":
        return get_taiwan_drug_service().translate_drug_name(arguments["name"])

    if name == "list_prior_authorization_drugs":
        return await get_taiwan_drug_service().get_prior_authorization_drugs()

    raise ValueError(f"Unknown tool: {name}")


def create_streamable_http_app(
    *,
    host: str | None = None,
    port: int | None = None,
    mount_path: str | None = None,
    streamable_http_path: str | None = None,
    stateless_http: bool | None = None,
) -> Starlette:
    """Create an ASGI app for Streamable HTTP deployments."""
    server = create_server(
        host=host,
        port=port,
        mount_path=mount_path,
        streamable_http_path=streamable_http_path,
        stateless_http=stateless_http,
    )
    streamable_app = server.streamable_http_app()
    configured_mount_path = server.settings.mount_path
    if configured_mount_path in {"", "/"}:
        return streamable_app

    def lifespan(_app: Starlette) -> Any:
        return server.session_manager.run()

    return Starlette(
        routes=[Mount(configured_mount_path, app=streamable_app)],
        lifespan=lifespan,
    )


def run_streamable_http_app(
    *,
    host: str,
    port: int,
    mount_path: str,
    streamable_http_path: str,
    stateless_http: bool,
) -> None:
    """Run the mounted Streamable HTTP ASGI app via uvicorn."""
    import uvicorn

    streamable_app = create_streamable_http_app(
        host=host,
        port=port,
        mount_path=mount_path,
        streamable_http_path=streamable_http_path,
        stateless_http=stateless_http,
    )
    config = uvicorn.Config(
        streamable_app,
        host=host,
        port=port,
        log_level="info",
    )
    uvicorn.Server(config).run()


class LazyStreamableHTTPApp:
    """ASGI wrapper that defers MCP server creation until first request."""

    def __init__(self) -> None:
        self._app: Starlette | None = None

    @property
    def app(self) -> Starlette:
        """Return the initialized Streamable HTTP app."""
        if self._app is None:
            self._app = create_streamable_http_app()
        return self._app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        await self.app(scope, receive, send)


def create_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for server startup."""
    parser = argparse.ArgumentParser(description="Run the Pharmacy MCP server.")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default=settings.transport,
        help="Transport to expose for MCP clients.",
    )
    parser.add_argument(
        "--host",
        default=settings.host,
        help="Host for HTTP-based transports.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.port,
        help="Port for HTTP-based transports.",
    )
    parser.add_argument(
        "--mount-path",
        default=settings.mount_path,
        help="ASGI mount path for HTTP-based transports.",
    )
    parser.add_argument(
        "--streamable-http-path",
        default=settings.streamable_http_path,
        help="Path for the Streamable HTTP MCP endpoint.",
    )
    parser.add_argument(
        "--stateless-http",
        action="store_true",
        default=settings.stateless_http,
        help="Enable stateless Streamable HTTP mode.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Main entry point for stdio and HTTP transports."""
    logging.basicConfig(level=logging.INFO)
    args = create_parser().parse_args(list(argv) if argv is not None else None)
    if args.transport == "streamable-http":
        logger.info("Pharmacy MCP Server starting with transport=%s", args.transport)
        run_streamable_http_app(
            host=args.host,
            port=args.port,
            mount_path=args.mount_path,
            streamable_http_path=args.streamable_http_path,
            stateless_http=args.stateless_http,
        )
        return

    server = create_server(
        host=args.host,
        port=args.port,
        mount_path=args.mount_path,
        streamable_http_path=args.streamable_http_path,
        stateless_http=args.stateless_http,
    )
    logger.info("Pharmacy MCP Server starting with transport=%s", args.transport)
    server.run(transport=args.transport, mount_path=args.mount_path)


app = LazyStreamableHTTPApp()


if __name__ == "__main__":
    main()
