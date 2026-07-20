"""MCP Server entry point."""

import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    TextContent,
    Tool,
)

from pharmacy_mcp.application.harness import AGENT_CONTRACT_NAME, build_agent_contract
from pharmacy_mcp.application.services.dosage import DosageService
from pharmacy_mcp.application.services.drug_info import DrugInfoService
from pharmacy_mcp.application.services.drug_search import DrugSearchService
from pharmacy_mcp.application.services.interaction import InteractionService
from pharmacy_mcp.application.services.prescription import PrescriptionService
from pharmacy_mcp.application.services.taiwan_drug import TaiwanDrugService
from pharmacy_mcp.application.services.unified_query import UnifiedQueryService
from pharmacy_mcp.config import settings
from pharmacy_mcp.domain.models.provider import QueryCapability
from pharmacy_mcp.domain.models.response import (
    OutputFormat,
    QueryResponse,
    ServiceResult,
)
from pharmacy_mcp.infrastructure.providers.catalog import PROVIDER_CATALOG
from pharmacy_mcp.infrastructure.providers.registry import build_default_registry
from pharmacy_mcp.presentation.formatting import ResponseFormatter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    "description": "BCP 47 locale for labels and messages (for example zh-TW or en-US).",
}

# Initialize services
drug_search_service = DrugSearchService()
drug_info_service = DrugInfoService()
interaction_service = InteractionService()
dosage_service = DosageService()
taiwan_drug_service = TaiwanDrugService()
prescription_service = PrescriptionService()
provider_registry = build_default_registry()
unified_query_service = UnifiedQueryService(provider_registry)


def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server("pharmacy-mcp")

    @server.list_tools()  # type: ignore[no-untyped-call,untyped-decorator]
    async def list_tools() -> list[Tool]:
        """List all available pharmacy tools."""
        return _decorate_tools(
            [
                Tool(
                    name="query_pharmacy",
                    description=(
                        "Single pharmaceutical knowledge entry point. Queries selected "
                        "API, Taiwan, hospital, database, document, vector, and web "
                        "providers concurrently and preserves partial failures."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 500,
                                "description": "Drug, identifier, indication, or question.",
                            },
                            "capabilities": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": [item.value for item in QueryCapability],
                                },
                                "default": ["search"],
                                "uniqueItems": True,
                                "description": "Knowledge capabilities required by the query.",
                            },
                            "sources": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": [item.id for item in PROVIDER_CATALOG],
                                },
                                "uniqueItems": True,
                                "description": (
                                    "Explicit providers. Omit to use enabled compatible sources."
                                ),
                            },
                            "limit": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 100,
                                "default": 10,
                            },
                            "context": {
                                "type": "object",
                                "description": (
                                    "Optional provider routing context. Do not put secrets here."
                                ),
                            },
                        },
                        "required": ["query"],
                        "additionalProperties": False,
                    },
                ),
                Tool(
                    name="list_knowledge_sources",
                    description=(
                        "List every cataloged pharmaceutical knowledge source and its "
                        "capabilities, readiness, credential requirements, and actual "
                        "runtime registration state."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "state": {
                                "type": "string",
                                "enum": [
                                    "ready",
                                    "configurable",
                                    "license_required",
                                    "deprecated",
                                ],
                                "description": "Optional readiness filter.",
                            },
                            "capability": {
                                "type": "string",
                                "enum": [item.value for item in QueryCapability],
                                "description": "Optional capability filter.",
                            },
                        },
                        "additionalProperties": False,
                    },
                ),
                Tool(
                    name="get_nhi_data_status",
                    description=(
                        "Inspect Taiwan NHI official CSV index freshness, row count, "
                        "local path, and upstream dataset URL without downloading data."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                ),
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
                        "required": [
                            "age_years",
                            "weight_kg",
                            "serum_creatinine",
                            "gender",
                        ],
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
                        "required": [
                            "total_dose",
                            "dose_unit",
                            "volume_ml",
                            "duration_hours",
                        ],
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
                                "enum": [
                                    "name",
                                    "ingredient",
                                    "permit_number",
                                    "manufacturer",
                                ],
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
                # ========== Prescription Tools (處方工具) ==========
                Tool(
                    name="get_formulary_item",
                    description="取得院內藥品詳情。Get hospital formulary item details by drug code.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "drug_code": {
                                "type": "string",
                                "description": "Hospital drug code (e.g., GENTA-INJ, VANCO-INJ)",
                            },
                        },
                        "required": ["drug_code"],
                    },
                ),
                Tool(
                    name="search_formulary",
                    description="搜尋院內藥品檔。Search hospital formulary by drug name or code.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (drug name, generic name, or code)",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results (default: 10)",
                                "default": 10,
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="get_renal_adjustment",
                    description="取得腎功能劑量調整建議。Get renal dosing adjustment recommendation based on CrCl.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "drug_code": {
                                "type": "string",
                                "description": "Hospital drug code",
                            },
                            "crcl": {
                                "type": "number",
                                "description": "Creatinine clearance in mL/min",
                            },
                        },
                        "required": ["drug_code", "crcl"],
                    },
                ),
                Tool(
                    name="validate_order",
                    description="驗證醫囑。Validate a medication order before submission.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "drug_code": {
                                "type": "string",
                                "description": "Hospital drug code",
                            },
                            "dose": {
                                "type": "number",
                                "description": "Dose value",
                            },
                            "dose_unit": {
                                "type": "string",
                                "description": "Dose unit (mg, g, mL, etc.)",
                            },
                            "route": {
                                "type": "string",
                                "description": "Route of administration (PO, IV, IM, SC, etc.)",
                            },
                            "frequency": {
                                "type": "string",
                                "description": "Dosing frequency (QD, BID, TID, Q8H, etc.)",
                            },
                            "patient_crcl": {
                                "type": "number",
                                "description": "Patient CrCl in mL/min (optional, for renal adjustment)",
                            },
                        },
                        "required": [
                            "drug_code",
                            "dose",
                            "dose_unit",
                            "route",
                            "frequency",
                        ],
                    },
                ),
                Tool(
                    name="submit_order",
                    description="送出醫囑到 HIS。Submit a medication order to HIS.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "patient_id": {
                                "type": "string",
                                "description": "Patient ID",
                            },
                            "drug_code": {
                                "type": "string",
                                "description": "Hospital drug code",
                            },
                            "dose": {
                                "type": "number",
                                "description": "Dose value",
                            },
                            "dose_unit": {
                                "type": "string",
                                "description": "Dose unit",
                            },
                            "route": {
                                "type": "string",
                                "description": "Route of administration",
                            },
                            "frequency": {
                                "type": "string",
                                "description": "Dosing frequency",
                            },
                            "duration_days": {
                                "type": "integer",
                                "description": "Treatment duration in days",
                            },
                            "physician_id": {
                                "type": "string",
                                "description": "Prescribing physician ID",
                            },
                            "override_warnings": {
                                "type": "boolean",
                                "description": "Override warnings and submit anyway",
                                "default": False,
                            },
                            "notes": {
                                "type": "string",
                                "description": "Optional notes for the order",
                            },
                        },
                        "required": [
                            "patient_id",
                            "drug_code",
                            "dose",
                            "dose_unit",
                            "route",
                            "frequency",
                            "duration_days",
                            "physician_id",
                        ],
                    },
                ),
                Tool(
                    name="stop_order",
                    description="停止醫囑。Discontinue an active medication order.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "order_id": {
                                "type": "string",
                                "description": "Order ID to discontinue",
                            },
                            "reason": {
                                "type": "string",
                                "description": "Reason for discontinuation",
                            },
                        },
                        "required": ["order_id", "reason"],
                    },
                ),
            ]
        )

    @server.call_tool()  # type: ignore[untyped-decorator]
    async def call_tool(
        name: str,
        arguments: dict[str, Any],
    ) -> tuple[list[TextContent], dict[str, Any]] | CallToolResult:
        """Handle tool calls using the versioned, agent-safe response contract."""

        output_format = _parse_output_format(arguments.get("output_format"))
        locale = str(arguments.get("locale", settings.default_locale))
        service_arguments = {
            key: value
            for key, value in arguments.items()
            if key not in {"output_format", "locale"}
        }
        try:
            result = await _handle_tool(name, service_arguments)
            if isinstance(result, ServiceResult):
                response = QueryResponse.from_service(
                    tool=name,
                    result=result,
                    output_format=output_format,
                    locale=locale,
                    disclaimer=settings.disclaimer,
                )
            else:
                response = QueryResponse.success(
                    tool=name,
                    data=result,
                    output_format=output_format,
                    locale=locale,
                    disclaimer=settings.disclaimer,
                )
            structured = response.model_dump(mode="json")
            return (
                [
                    TextContent(
                        type="text",
                        text=ResponseFormatter.render(response, output_format),
                    )
                ],
                structured,
            )
        except Exception as exc:
            logger.exception("Error in tool %s", name)
            response = QueryResponse.failure(
                tool=name,
                code="tool_execution_error",
                message=str(exc),
                output_format=output_format,
                locale=locale,
                disclaimer=settings.disclaimer,
                retryable=False,
            )
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=ResponseFormatter.render(response, output_format),
                    )
                ],
                structuredContent=response.model_dump(mode="json"),
                isError=True,
            )

    @server.list_prompts()  # type: ignore[no-untyped-call,untyped-decorator]
    async def list_prompts() -> list[Prompt]:
        """Expose the stable agent consumption contract to MCP clients."""

        return [
            Prompt(
                name=AGENT_CONTRACT_NAME,
                title="Pharmacy query output contract",
                description=(
                    "Instructions that constrain an agent to the versioned "
                    "QueryResponse envelope and source-preserving behavior."
                ),
                arguments=[
                    PromptArgument(
                        name="output_format",
                        description="json, json_compact, or markdown",
                        required=False,
                    ),
                    PromptArgument(
                        name="locale",
                        description="BCP 47 response locale, such as zh-TW",
                        required=False,
                    ),
                ],
            )
        ]

    @server.get_prompt()  # type: ignore[no-untyped-call,untyped-decorator]
    async def get_prompt(
        name: str,
        arguments: dict[str, str] | None,
    ) -> GetPromptResult:
        """Return parameterized instructions for the selected rendering."""

        if name != AGENT_CONTRACT_NAME:
            raise ValueError(f"Unknown prompt: {name}")
        prompt_arguments = arguments or {}
        output_format = _parse_output_format(prompt_arguments.get("output_format"))
        locale = prompt_arguments.get("locale", settings.default_locale)
        return GetPromptResult(
            description="Pharmacy MCP agent query and response contract.",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=build_agent_contract(output_format, locale),
                    ),
                )
            ],
        )

    return server


def _decorate_tools(tools: list[Tool]) -> list[Tool]:
    """Apply the same input/output contract and agent instruction to every tool."""

    for tool in tools:
        properties = tool.inputSchema.setdefault("properties", {})
        properties["output_format"] = OUTPUT_FORMAT_PROPERTY.copy()
        properties["locale"] = LOCALE_PROPERTY.copy()
        tool.outputSchema = OUTPUT_SCHEMA
        tool.description = (
            f"{tool.description or ''} "
            "Agent contract: use structuredContent as the source of truth; "
            "preserve schema_version/status/sources/warnings/errors/meta when "
            "forwarding the result and never infer missing clinical facts."
        ).strip()
    return tools


def _parse_output_format(value: Any) -> OutputFormat:
    """Resolve a requested output format after JSON Schema input validation."""

    return OutputFormat(value or settings.default_output_format)


async def _handle_tool(
    name: str,
    arguments: dict[str, Any],
) -> dict[str, Any] | ServiceResult:
    """Route tool calls to appropriate service methods."""

    if name == "query_pharmacy":
        return await unified_query_service.query(
            text=arguments["query"],
            capabilities=arguments.get("capabilities"),
            sources=arguments.get("sources"),
            limit=arguments.get("limit", 10),
            context=arguments.get("context"),
        )

    if name == "list_knowledge_sources":
        catalog = provider_registry.catalog()
        state = arguments.get("state")
        capability = arguments.get("capability")
        if state:
            catalog = [item for item in catalog if item["state"] == state]
        if capability:
            catalog = [item for item in catalog if capability in item["capabilities"]]
        return {"count": len(catalog), "providers": catalog}

    if name == "get_nhi_data_status":
        return taiwan_drug_service.get_nhi_data_status()

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

    # Prescription tools (處方工具)
    elif name == "get_formulary_item":
        item = prescription_service.get_formulary_item(arguments["drug_code"])
        if item:
            return item.to_dict()
        return {"error": f"Drug code {arguments['drug_code']} not found in formulary"}

    elif name == "search_formulary":
        items = prescription_service.search_formulary(
            query=arguments["query"],
            limit=arguments.get("limit", 10),
        )
        return {
            "count": len(items),
            "items": [item.to_dict() for item in items],
        }

    elif name == "get_renal_adjustment":
        adjustment = prescription_service.get_renal_adjustment(
            drug_code=arguments["drug_code"],
            crcl=arguments["crcl"],
        )
        return adjustment.to_dict()

    elif name == "validate_order":
        validation = prescription_service.validate_order(
            drug_code=arguments["drug_code"],
            dose=arguments["dose"],
            dose_unit=arguments["dose_unit"],
            route=arguments["route"],
            frequency=arguments["frequency"],
            patient_crcl=arguments.get("patient_crcl"),
        )
        return validation.to_dict()

    elif name == "submit_order":
        order_result = await prescription_service.submit_order(
            patient_id=arguments["patient_id"],
            drug_code=arguments["drug_code"],
            dose=arguments["dose"],
            dose_unit=arguments["dose_unit"],
            route=arguments["route"],
            frequency=arguments["frequency"],
            duration_days=arguments["duration_days"],
            physician_id=arguments["physician_id"],
            override_warnings=arguments.get("override_warnings", False),
            notes=arguments.get("notes"),
        )
        return order_result.to_dict()

    elif name == "stop_order":
        stop_result = await prescription_service.stop_order(
            order_id=arguments["order_id"],
            reason=arguments["reason"],
        )
        return stop_result.to_dict()

    else:
        return {"error": f"Unknown tool: {name}"}


async def run_server() -> None:
    """Run the MCP server."""
    server = create_server()

    async with stdio_server() as (read_stream, write_stream):
        logger.info("Pharmacy MCP Server starting...")
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    """Main entry point."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
