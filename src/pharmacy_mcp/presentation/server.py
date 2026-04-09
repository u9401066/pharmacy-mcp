"""MCP Server entry point and deployment helpers."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from typing import Any

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette

from pharmacy_mcp.application.services.dosage import DosageService
from pharmacy_mcp.application.services.drug_info import DrugInfoService
from pharmacy_mcp.application.services.drug_search import DrugSearchService
from pharmacy_mcp.application.services.interaction import InteractionService
from pharmacy_mcp.application.services.prescription import PrescriptionService
from pharmacy_mcp.application.services.taiwan_drug import TaiwanDrugService
from pharmacy_mcp.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SERVER_NAME = "pharmacy-mcp"
SERVER_INSTRUCTIONS = (
    "Provide pharmacy reference information for educational and workflow support. "
    f"Always include the project disclaimer: {settings.disclaimer}"
)
SERVER_WEBSITE_URL = "https://github.com/u9401066/pharmacy-mcp"

# Initialize services once and reuse them across transports.
drug_search_service = DrugSearchService()
drug_info_service = DrugInfoService()
interaction_service = InteractionService()
dosage_service = DosageService()
taiwan_drug_service = TaiwanDrugService()
prescription_service = PrescriptionService()


ToolResult = dict[str, Any]


def create_server(
    *,
    host: str | None = None,
    port: int | None = None,
    mount_path: str | None = None,
    streamable_http_path: str | None = None,
    stateless_http: bool | None = None,
) -> FastMCP:
    """Create and configure the MCP server using FastMCP."""
    server = FastMCP(
        name=SERVER_NAME,
        instructions=SERVER_INSTRUCTIONS,
        website_url=SERVER_WEBSITE_URL,
        host=host or settings.host,
        port=port or settings.port,
        mount_path=mount_path or settings.mount_path,
        streamable_http_path=streamable_http_path or settings.streamable_http_path,
        stateless_http=(
            settings.stateless_http
            if stateless_http is None
            else stateless_http
        ),
        log_level="INFO",
    )

    @server.tool(description="Search for drugs by name. Returns results from RxNorm and FDA databases.")
    async def search_drug(query: str, max_results: int = 10) -> ToolResult:
        return await _handle_tool(
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
        return await _handle_tool("get_drug_info", {"drug_name": drug_name})

    @server.tool(description="Get dosage and administration information for a drug.")
    async def get_drug_dosage(drug_name: str) -> ToolResult:
        return await _handle_tool("get_drug_dosage", {"drug_name": drug_name})

    @server.tool(
        description="Get warnings, contraindications, and adverse reactions for a drug."
    )
    async def get_drug_warnings(drug_name: str) -> ToolResult:
        return await _handle_tool("get_drug_warnings", {"drug_name": drug_name})

    @server.tool(description="Check for interactions between two drugs.")
    async def check_drug_interaction(drug1: str, drug2: str) -> ToolResult:
        return await _handle_tool("check_drug_interaction", {"drug1": drug1, "drug2": drug2})

    @server.tool(
        description="Check for interactions among multiple drugs (medication list review)."
    )
    async def check_multi_drug_interactions(drugs: list[str]) -> ToolResult:
        return await _handle_tool("check_multi_drug_interactions", {"drugs": drugs})

    @server.tool(description="Check for food-drug interactions for a specific drug.")
    async def check_food_drug_interaction(drug_name: str) -> ToolResult:
        return await _handle_tool("check_food_drug_interaction", {"drug_name": drug_name})

    @server.tool(description="Calculate weight-based dosage (mg/kg).")
    def calculate_dose_by_weight(
        dose_per_kg: float,
        patient_weight_kg: float,
        dose_unit: str = "mg",
        max_dose: float | None = None,
    ) -> ToolResult:
        return dosage_service.calculate_weight_based_dose(
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
        return dosage_service.calculate_bsa_based_dose(
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
        return dosage_service.calculate_creatinine_clearance(
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
        return dosage_service.calculate_pediatric_dose(
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
        return dosage_service.calculate_infusion_rate(
            total_dose=total_dose,
            dose_unit=dose_unit,
            volume_ml=volume_ml,
            duration_hours=duration_hours,
        )

    @server.tool(description="Convert between dose units (g, mg, mcg, ng).")
    def convert_dose_units(value: float, from_unit: str, to_unit: str) -> ToolResult:
        return dosage_service.convert_dose_units(
            value=value,
            from_unit=from_unit,
            to_unit=to_unit,
        )

    @server.tool(
        description=(
            "搜尋台灣 TFDA 藥品資料庫。Search Taiwan TFDA drug database for "
            "drug permits and information."
        )
    )
    async def search_tfda_drug(
        query: str,
        search_type: str = "name",
        limit: int = 20,
    ) -> ToolResult:
        return await _handle_tool(
            "search_tfda_drug",
            {"query": query, "search_type": search_type, "limit": limit},
        )

    @server.tool(
        description=(
            "查詢藥品健保給付狀態。Check if a drug is covered by Taiwan National "
            "Health Insurance (NHI) and get coverage details."
        )
    )
    async def get_nhi_coverage(drug_name: str) -> ToolResult:
        return await _handle_tool("get_nhi_coverage", {"drug_name": drug_name})

    @server.tool(description="查詢健保藥價。Get NHI reimbursement price for a drug by NHI code.")
    async def get_nhi_drug_price(nhi_code: str) -> ToolResult:
        return await _handle_tool("get_nhi_drug_price", {"nhi_code": nhi_code})

    @server.tool(
        description=(
            "藥品名稱中英對照。Translate drug names between English and Chinese "
            "(Traditional)."
        )
    )
    async def translate_drug_name(name: str) -> ToolResult:
        return await _handle_tool("translate_drug_name", {"name": name})

    @server.tool(
        description="列出需事前審查的健保藥品。List drugs requiring NHI prior authorization."
    )
    async def list_prior_authorization_drugs() -> ToolResult:
        return await _handle_tool("list_prior_authorization_drugs", {})

    @server.tool(
        description="列出健保給付規則資料庫。List all NHI coverage rules in the database."
    )
    def list_nhi_coverage_rules() -> ToolResult:
        return taiwan_drug_service.list_nhi_coverage_rules()

    @server.tool(
        description="取得院內藥品詳情。Get hospital formulary item details by drug code."
    )
    def get_formulary_item(drug_code: str) -> ToolResult:
        item = prescription_service.get_formulary_item(drug_code)
        if item:
            return item.to_dict()
        return {"error": f"Drug code {drug_code} not found in formulary"}

    @server.tool(description="搜尋院內藥品檔。Search hospital formulary by drug name or code.")
    def search_formulary(query: str, limit: int = 10) -> ToolResult:
        items = prescription_service.search_formulary(query=query, limit=limit)
        return {"count": len(items), "items": [item.to_dict() for item in items]}

    @server.tool(
        description=(
            "取得腎功能劑量調整建議。Get renal dosing adjustment recommendation "
            "based on CrCl."
        )
    )
    def get_renal_adjustment(drug_code: str, crcl: float) -> ToolResult:
        adjustment = prescription_service.get_renal_adjustment(drug_code=drug_code, crcl=crcl)
        return adjustment.to_dict()

    @server.tool(description="驗證醫囑。Validate a medication order before submission.")
    def validate_order(
        drug_code: str,
        dose: float,
        dose_unit: str,
        route: str,
        frequency: str,
        patient_crcl: float | None = None,
    ) -> ToolResult:
        result = prescription_service.validate_order(
            drug_code=drug_code,
            dose=dose,
            dose_unit=dose_unit,
            route=route,
            frequency=frequency,
            patient_crcl=patient_crcl,
        )
        return result.to_dict()

    @server.tool(description="送出醫囑到 HIS。Submit a medication order to the HIS service.")
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
        result = await prescription_service.submit_order(
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

    @server.tool(description="停止醫囑。Discontinue an active medication order.")
    async def stop_order(order_id: str, reason: str) -> ToolResult:
        result = await prescription_service.stop_order(order_id=order_id, reason=reason)
        return result.to_dict()

    return server


async def _handle_tool(name: str, arguments: dict[str, Any]) -> ToolResult:
    """Route tool calls to appropriate service methods."""
    if name == "search_drug":
        return await drug_search_service.search(
            query=arguments["query"],
            max_results=arguments.get("max_results", 10),
        )

    if name == "get_drug_info":
        return await drug_info_service.get_full_info(arguments["drug_name"])

    if name == "get_drug_dosage":
        return await drug_info_service.get_dosage_info(arguments["drug_name"])

    if name == "get_drug_warnings":
        return await drug_info_service.get_warnings(arguments["drug_name"])

    if name == "check_drug_interaction":
        return await interaction_service.check_drug_drug_interaction(
            drug1=arguments["drug1"],
            drug2=arguments["drug2"],
        )

    if name == "check_multi_drug_interactions":
        return await interaction_service.check_multi_drug_interactions(arguments["drugs"])

    if name == "check_food_drug_interaction":
        return await interaction_service.check_food_drug_interaction(arguments["drug_name"])

    if name == "search_tfda_drug":
        return await taiwan_drug_service.search_tfda_drug(
            query=arguments["query"],
            limit=arguments.get("limit", 20),
            search_type=arguments.get("search_type", "name"),
        )

    if name == "get_nhi_coverage":
        return await taiwan_drug_service.get_nhi_coverage(arguments["drug_name"])

    if name == "get_nhi_drug_price":
        return await taiwan_drug_service.get_nhi_drug_price(arguments["nhi_code"])

    if name == "translate_drug_name":
        return taiwan_drug_service.translate_drug_name(arguments["name"])

    if name == "list_prior_authorization_drugs":
        return await taiwan_drug_service.get_prior_authorization_drugs()

    raise ValueError(f"Unknown async tool: {name}")


def create_streamable_http_app() -> Starlette:
    """Create an ASGI app for Streamable HTTP deployments."""
    return create_server().streamable_http_app()


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
    args = create_parser().parse_args(list(argv) if argv is not None else None)
    server = create_server(
        host=args.host,
        port=args.port,
        mount_path=args.mount_path,
        streamable_http_path=args.streamable_http_path,
        stateless_http=args.stateless_http,
    )
    logger.info("Pharmacy MCP Server starting with transport=%s", args.transport)
    server.run(transport=args.transport, mount_path=args.mount_path)


app = create_streamable_http_app()


if __name__ == "__main__":
    main()
