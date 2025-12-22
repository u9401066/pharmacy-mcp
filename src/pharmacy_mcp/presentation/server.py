"""MCP Server entry point."""

import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from pharmacy_mcp.application.services.drug_search import DrugSearchService
from pharmacy_mcp.application.services.drug_info import DrugInfoService
from pharmacy_mcp.application.services.interaction import InteractionService
from pharmacy_mcp.application.services.dosage import DosageService
from pharmacy_mcp.application.services.taiwan_drug import TaiwanDrugService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
drug_search_service = DrugSearchService()
drug_info_service = DrugInfoService()
interaction_service = InteractionService()
dosage_service = DosageService()
taiwan_drug_service = TaiwanDrugService()


def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server("pharmacy-mcp")
    
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List all available pharmacy tools."""
        return [
            Tool(
                name="search_drug",
                description="Search for drugs by name. Returns results from RxNorm and FDA databases.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Drug name to search for",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 10)",
                            "default": 10,
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="get_drug_info",
                description="Get comprehensive information about a drug including indications, dosage, warnings, and pharmacology.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "drug_name": {
                            "type": "string",
                            "description": "Name of the drug",
                        },
                    },
                    "required": ["drug_name"],
                },
            ),
            Tool(
                name="get_drug_dosage",
                description="Get dosage and administration information for a drug.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "drug_name": {
                            "type": "string",
                            "description": "Name of the drug",
                        },
                    },
                    "required": ["drug_name"],
                },
            ),
            Tool(
                name="get_drug_warnings",
                description="Get warnings, contraindications, and adverse reactions for a drug.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "drug_name": {
                            "type": "string",
                            "description": "Name of the drug",
                        },
                    },
                    "required": ["drug_name"],
                },
            ),
            Tool(
                name="check_drug_interaction",
                description="Check for interactions between two drugs.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "drug1": {
                            "type": "string",
                            "description": "First drug name",
                        },
                        "drug2": {
                            "type": "string",
                            "description": "Second drug name",
                        },
                    },
                    "required": ["drug1", "drug2"],
                },
            ),
            Tool(
                name="check_multi_drug_interactions",
                description="Check for interactions among multiple drugs (medication list review).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "drugs": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of drug names to check",
                        },
                    },
                    "required": ["drugs"],
                },
            ),
            Tool(
                name="check_food_drug_interaction",
                description="Check for food-drug interactions for a specific drug.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "drug_name": {
                            "type": "string",
                            "description": "Name of the drug",
                        },
                    },
                    "required": ["drug_name"],
                },
            ),
            Tool(
                name="calculate_dose_by_weight",
                description="Calculate weight-based dosage (mg/kg).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "dose_per_kg": {
                            "type": "number",
                            "description": "Dose per kg of body weight",
                        },
                        "patient_weight_kg": {
                            "type": "number",
                            "description": "Patient weight in kg",
                        },
                        "dose_unit": {
                            "type": "string",
                            "description": "Unit of dose (default: mg)",
                            "default": "mg",
                        },
                        "max_dose": {
                            "type": "number",
                            "description": "Maximum dose cap (optional)",
                        },
                    },
                    "required": ["dose_per_kg", "patient_weight_kg"],
                },
            ),
            Tool(
                name="calculate_dose_by_bsa",
                description="Calculate BSA-based dosage (mg/m²), commonly used in oncology.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "dose_per_m2": {
                            "type": "number",
                            "description": "Dose per m² of body surface area",
                        },
                        "height_cm": {
                            "type": "number",
                            "description": "Patient height in cm",
                        },
                        "weight_kg": {
                            "type": "number",
                            "description": "Patient weight in kg",
                        },
                        "dose_unit": {
                            "type": "string",
                            "description": "Unit of dose (default: mg)",
                            "default": "mg",
                        },
                        "max_dose": {
                            "type": "number",
                            "description": "Maximum dose cap (optional)",
                        },
                    },
                    "required": ["dose_per_m2", "height_cm", "weight_kg"],
                },
            ),
            Tool(
                name="calculate_creatinine_clearance",
                description="Calculate creatinine clearance using Cockcroft-Gault formula for renal dosing adjustments.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "age_years": {
                            "type": "integer",
                            "description": "Patient age in years",
                        },
                        "weight_kg": {
                            "type": "number",
                            "description": "Patient weight in kg",
                        },
                        "serum_creatinine": {
                            "type": "number",
                            "description": "Serum creatinine in mg/dL",
                        },
                        "gender": {
                            "type": "string",
                            "description": "Patient gender (m/f or male/female)",
                        },
                    },
                    "required": ["age_years", "weight_kg", "serum_creatinine", "gender"],
                },
            ),
            Tool(
                name="calculate_pediatric_dose",
                description="Calculate pediatric dose from adult dose using weight, age, or BSA method.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "adult_dose": {
                            "type": "number",
                            "description": "Standard adult dose",
                        },
                        "child_weight_kg": {
                            "type": "number",
                            "description": "Child's weight in kg",
                        },
                        "method": {
                            "type": "string",
                            "description": "Calculation method: weight, age, or bsa",
                            "enum": ["weight", "age", "bsa"],
                            "default": "weight",
                        },
                        "child_age_years": {
                            "type": "integer",
                            "description": "Child's age in years (required for age method)",
                        },
                        "child_bsa": {
                            "type": "number",
                            "description": "Child's BSA in m² (required for bsa method)",
                        },
                        "dose_unit": {
                            "type": "string",
                            "description": "Unit of dose (default: mg)",
                            "default": "mg",
                        },
                    },
                    "required": ["adult_dose", "child_weight_kg"],
                },
            ),
            Tool(
                name="calculate_infusion_rate",
                description="Calculate IV infusion rate.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "total_dose": {
                            "type": "number",
                            "description": "Total dose to infuse",
                        },
                        "dose_unit": {
                            "type": "string",
                            "description": "Unit of dose",
                        },
                        "volume_ml": {
                            "type": "number",
                            "description": "Total volume in mL",
                        },
                        "duration_hours": {
                            "type": "number",
                            "description": "Infusion duration in hours",
                        },
                    },
                    "required": ["total_dose", "dose_unit", "volume_ml", "duration_hours"],
                },
            ),
            Tool(
                name="convert_dose_units",
                description="Convert between dose units (g, mg, mcg, ng).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "value": {
                            "type": "number",
                            "description": "Dose value to convert",
                        },
                        "from_unit": {
                            "type": "string",
                            "description": "Source unit (g, mg, mcg, ng)",
                        },
                        "to_unit": {
                            "type": "string",
                            "description": "Target unit (g, mg, mcg, ng)",
                        },
                    },
                    "required": ["value", "from_unit", "to_unit"],
                },
            ),
            # ========== Taiwan Drug Tools (台灣藥品工具) ==========
            Tool(
                name="search_tfda_drug",
                description="搜尋台灣 TFDA 藥品資料庫。Search Taiwan TFDA drug database for drug permits and information.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (drug name in Chinese or English)",
                        },
                        "search_type": {
                            "type": "string",
                            "description": "Type of search: name (default), ingredient, permit_number, manufacturer",
                            "enum": ["name", "ingredient", "permit_number", "manufacturer"],
                            "default": "name",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 20)",
                            "default": 20,
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="get_nhi_coverage",
                description="查詢藥品健保給付狀態。Check if a drug is covered by Taiwan National Health Insurance (NHI) and get coverage details.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "drug_name": {
                            "type": "string",
                            "description": "Drug name (generic or brand name)",
                        },
                    },
                    "required": ["drug_name"],
                },
            ),
            Tool(
                name="get_nhi_drug_price",
                description="查詢健保藥價。Get NHI reimbursement price for a drug by NHI code.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "nhi_code": {
                            "type": "string",
                            "description": "NHI drug code (e.g., A022664100)",
                        },
                    },
                    "required": ["nhi_code"],
                },
            ),
            Tool(
                name="translate_drug_name",
                description="藥品名稱中英對照。Translate drug names between English and Chinese (Traditional).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Drug name to translate (English or Chinese)",
                        },
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="list_prior_authorization_drugs",
                description="列出需事前審查的健保藥品。List drugs requiring NHI prior authorization.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="list_nhi_coverage_rules",
                description="列出健保給付規則資料庫。List all NHI coverage rules in the database.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle tool calls."""
        import json
        
        try:
            result = await _handle_tool(name, arguments)
            return [TextContent(
                type="text",
                text=json.dumps(result, ensure_ascii=False, indent=2)
            )]
        except Exception as e:
            logger.error(f"Error in tool {name}: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, ensure_ascii=False)
            )]
    
    return server


async def _handle_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Route tool calls to appropriate service methods."""
    
    # Drug search tools
    if name == "search_drug":
        return await drug_search_service.search(
            query=arguments["query"],
            max_results=arguments.get("max_results", 10),
        )
    
    # Drug info tools
    elif name == "get_drug_info":
        return await drug_info_service.get_full_info(arguments["drug_name"])
    
    elif name == "get_drug_dosage":
        return await drug_info_service.get_dosage_info(arguments["drug_name"])
    
    elif name == "get_drug_warnings":
        return await drug_info_service.get_warnings(arguments["drug_name"])
    
    # Interaction tools
    elif name == "check_drug_interaction":
        return await interaction_service.check_drug_drug_interaction(
            drug1=arguments["drug1"],
            drug2=arguments["drug2"],
        )
    
    elif name == "check_multi_drug_interactions":
        return await interaction_service.check_multi_drug_interactions(
            drugs=arguments["drugs"],
        )
    
    elif name == "check_food_drug_interaction":
        return await interaction_service.check_food_drug_interaction(
            drug_name=arguments["drug_name"],
        )
    
    # Dosage calculation tools
    elif name == "calculate_dose_by_weight":
        return dosage_service.calculate_weight_based_dose(
            dose_per_kg=arguments["dose_per_kg"],
            patient_weight_kg=arguments["patient_weight_kg"],
            dose_unit=arguments.get("dose_unit", "mg"),
            max_dose=arguments.get("max_dose"),
        )
    
    elif name == "calculate_dose_by_bsa":
        return dosage_service.calculate_bsa_based_dose(
            dose_per_m2=arguments["dose_per_m2"],
            height_cm=arguments["height_cm"],
            weight_kg=arguments["weight_kg"],
            dose_unit=arguments.get("dose_unit", "mg"),
            max_dose=arguments.get("max_dose"),
        )
    
    elif name == "calculate_creatinine_clearance":
        return dosage_service.calculate_creatinine_clearance(
            age_years=arguments["age_years"],
            weight_kg=arguments["weight_kg"],
            serum_creatinine=arguments["serum_creatinine"],
            gender=arguments["gender"],
        )
    
    elif name == "calculate_pediatric_dose":
        return dosage_service.calculate_pediatric_dose(
            adult_dose=arguments["adult_dose"],
            child_weight_kg=arguments["child_weight_kg"],
            dose_unit=arguments.get("dose_unit", "mg"),
            method=arguments.get("method", "weight"),
            child_age_years=arguments.get("child_age_years"),
            child_bsa=arguments.get("child_bsa"),
        )
    
    elif name == "calculate_infusion_rate":
        return dosage_service.calculate_infusion_rate(
            total_dose=arguments["total_dose"],
            dose_unit=arguments["dose_unit"],
            volume_ml=arguments["volume_ml"],
            duration_hours=arguments["duration_hours"],
        )
    
    elif name == "convert_dose_units":
        return dosage_service.convert_dose_units(
            value=arguments["value"],
            from_unit=arguments["from_unit"],
            to_unit=arguments["to_unit"],
        )
    
    # Taiwan drug tools (台灣藥品工具)
    elif name == "search_tfda_drug":
        return await taiwan_drug_service.search_tfda_drug(
            query=arguments["query"],
            limit=arguments.get("limit", 20),
            search_type=arguments.get("search_type", "name"),
        )
    
    elif name == "get_nhi_coverage":
        return await taiwan_drug_service.get_nhi_coverage(
            drug_name=arguments["drug_name"],
        )
    
    elif name == "get_nhi_drug_price":
        return await taiwan_drug_service.get_nhi_drug_price(
            nhi_code=arguments["nhi_code"],
        )
    
    elif name == "translate_drug_name":
        return taiwan_drug_service.translate_drug_name(
            name=arguments["name"],
        )
    
    elif name == "list_prior_authorization_drugs":
        return await taiwan_drug_service.get_prior_authorization_drugs()
    
    elif name == "list_nhi_coverage_rules":
        return taiwan_drug_service.list_nhi_coverage_rules()
    
    else:
        return {"error": f"Unknown tool: {name}"}


async def run_server():
    """Run the MCP server."""
    server = create_server()
    
    async with stdio_server() as (read_stream, write_stream):
        logger.info("Pharmacy MCP Server starting...")
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main():
    """Main entry point."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
