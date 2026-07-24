"""Tests for MCP server."""

import json
import subprocess
import sys

import pytest
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.testclient import TestClient

from pharmacy_mcp.config import settings
from pharmacy_mcp.presentation import server as server_module
from pharmacy_mcp.presentation.server import (
    app,
    create_server,
    create_streamable_http_app,
)

EXPECTED_TOOL_NAMES = {
    "query_pharmacy",
    "list_knowledge_sources",
    "get_nhi_data_status",
    "search_drug",
    "get_drug_info",
    "get_drug_dosage",
    "get_drug_warnings",
    "check_drug_interaction",
    "check_multi_drug_interactions",
    "check_food_drug_interaction",
    "calculate_dose_by_weight",
    "calculate_dose_by_bsa",
    "calculate_creatinine_clearance",
    "calculate_pediatric_dose",
    "calculate_infusion_rate",
    "convert_dose_units",
    "search_tfda_drug",
    "get_nhi_coverage",
    "get_nhi_drug_price",
    "translate_drug_name",
    "list_prior_authorization_drugs",
    "list_nhi_coverage_rules",
    "get_formulary_item",
    "search_formulary",
    "get_renal_adjustment",
    "validate_order",
    "submit_order",
    "stop_order",
    "list_formula_catalog",
    "get_formula_details",
    "explain_interaction_mechanism",
    "simulate_pk_interaction",
    "simulate_concentration_time",
}
EXPECTED_TOOL_COUNT = len(EXPECTED_TOOL_NAMES)

EXPECTED_RESOURCE_URIS = {
    "pharmacy://server/disclaimer",
    "pharmacy://formulas",
    "pharmacy://validation/formulas",
}

EXPECTED_RESOURCE_TEMPLATE_URIS = {
    "pharmacy://formulas/{formula_id}",
}

EXPECTED_PROMPT_NAMES = {
    "ddi_analysis_workflow",
    "formula_review_checklist",
    "pharmacy-query-contract",
}


class TestMCPServer:
    """Tests for MCP server."""

    def test_server_creation(self):
        """Test server can be created with metadata."""
        server = create_server()

        assert server is not None
        assert server.name == "pharmacy-mcp"
        assert settings.disclaimer in server.instructions

    async def test_server_registers_all_tools(self):
        """Test FastMCP registers the pharmacy tool catalog."""
        server = create_server()

        tools = await server.list_tools()
        tool_names = {tool.name for tool in tools}

        assert len(tools) == EXPECTED_TOOL_COUNT
        assert tool_names == EXPECTED_TOOL_NAMES

        search_tool = next(tool for tool in tools if tool.name == "search_drug")
        assert search_tool.inputSchema["properties"]["max_results"]["default"] == 10
        assert search_tool.inputSchema["properties"]["output_format"]["enum"] == [
            "json",
            "json_compact",
            "markdown",
        ]
        assert (
            search_tool.outputSchema["properties"]["schema_version"]["const"] == "1.0"
        )

    async def test_server_routes_structured_tool_calls(self):
        """Test registered FastMCP tools call the underlying services."""
        server = create_server()

        content, structured = await server.call_tool(
            "convert_dose_units",
            {"value": 1, "from_unit": "g", "to_unit": "mg"},
        )

        assert structured["schema_version"] == "1.0"
        assert structured["data"]["converted_value"] == 1000
        assert structured["data"]["converted_unit"] == "mg"
        assert content[0].text

    async def test_server_routes_simulation_tool_calls(self):
        """Test simulation tools return formula-backed structured output."""
        server = create_server()

        content, structured = await server.call_tool(
            "simulate_concentration_time",
            {"dose": 500, "vd": 50, "ke": 0.1, "time": 6},
        )

        assert structured["data"]["formula_id"] == "one_compartment_concentration"
        assert structured["data"]["outputs"]["concentration"] == 5.4881
        assert content[0].text

    async def test_server_routes_formula_and_mechanism_tool_calls(self):
        """Test catalog and DDI simulation tools route through FastMCP."""
        server = create_server()

        _, catalog = await server.call_tool("list_formula_catalog", {})
        _, formula = await server.call_tool(
            "get_formula_details",
            {"formula_id": "cyp_reversible_inhibition_clearance"},
        )
        _, missing_formula = await server.call_tool(
            "get_formula_details",
            {"formula_id": "missing_formula"},
        )
        _, mechanism = await server.call_tool(
            "explain_interaction_mechanism",
            {"drug1": "warfarin", "drug2": "fluconazole"},
        )
        _, simulation = await server.call_tool(
            "simulate_pk_interaction",
            {
                "drug1": "warfarin",
                "drug2": "fluconazole",
                "cl_total": 6,
                "fm": 0.85,
                "inhibitor_concentration": 4,
                "ki": 2,
            },
        )

        assert catalog["data"]["formula_count"] >= 6
        assert formula["data"]["id"] == "cyp_reversible_inhibition_clearance"
        assert missing_formula["data"]["error"] == "Formula missing_formula not found"
        assert mechanism["data"]["mechanism"]["pathway"] == "CYP2C9"
        assert simulation["data"]["simulation"]["outputs"]["auc_ratio"] > 1

    async def test_server_routes_prescription_tool_calls(self):
        """Test hospital workflow tools route through FastMCP."""
        server = create_server()

        _, formulary_item = await server.call_tool(
            "get_formulary_item",
            {"drug_code": "GENTA-INJ"},
        )
        _, missing_item = await server.call_tool(
            "get_formulary_item",
            {"drug_code": "NOPE"},
        )
        _, search_result = await server.call_tool(
            "search_formulary",
            {"query": "gentamicin", "limit": 5},
        )
        _, renal = await server.call_tool(
            "get_renal_adjustment",
            {"drug_code": "GENTA-INJ", "crcl": 25},
        )
        _, validation = await server.call_tool(
            "validate_order",
            {
                "drug_code": "GENTA-INJ",
                "dose": 80,
                "dose_unit": "mg",
                "route": "IV",
                "frequency": "q8h",
            },
        )

        assert formulary_item["data"]["drug_code"] == "GENTA-INJ"
        assert missing_item["data"]["error"] == "Drug code NOPE not found in formulary"
        assert search_result["data"]["count"] >= 1
        assert renal["data"]["drug_code"] == "GENTA-INJ"
        assert validation["data"]["valid"] is True

    async def test_server_exposes_formula_resources(self):
        """Test FastMCP exposes read-only formula resources."""
        server = create_server()

        resources = await server.list_resources()
        resource_uris = {str(resource.uri) for resource in resources}
        templates = await server.list_resource_templates()
        template_uris = {str(template.uriTemplate) for template in templates}

        assert EXPECTED_RESOURCE_URIS.issubset(resource_uris)
        assert EXPECTED_RESOURCE_TEMPLATE_URIS.issubset(template_uris)

        content = await server.read_resource("pharmacy://formulas")
        catalog = json.loads(content[0].content)
        assert catalog["version"] == "0.9.0"
        assert catalog["formula_count"] >= 6

        detail_content = await server.read_resource(
            "pharmacy://formulas/one_compartment_concentration"
        )
        detail = json.loads(detail_content[0].content)
        assert detail["id"] == "one_compartment_concentration"

        with pytest.raises(ValueError, match="Formula missing not found"):
            await server.read_resource("pharmacy://formulas/missing")

    async def test_server_exposes_workflow_prompts(self):
        """Test FastMCP exposes prompt templates for DDI workflows."""
        server = create_server()

        prompts = await server.list_prompts()
        prompt_names = {prompt.name for prompt in prompts}

        assert EXPECTED_PROMPT_NAMES.issubset(prompt_names)

        prompt = await server.get_prompt(
            "ddi_analysis_workflow",
            {"drug1": "warfarin", "drug2": "fluconazole"},
        )
        assert "warfarin" in prompt.messages[0].content.text
        assert settings.disclaimer in prompt.messages[0].content.text

    def test_streamable_http_app_creation(self):
        """Test Streamable HTTP deployment helper returns an ASGI app."""
        streamable_app = create_streamable_http_app()

        assert isinstance(streamable_app, Starlette)
        assert callable(app)
        assert app._app is None
        assert any(
            route.path == settings.streamable_http_path
            for route in streamable_app.routes
        )

    def test_create_server_preserves_explicit_falsy_options(self):
        """Test server factory does not replace intentional falsy overrides."""
        server = create_server(port=0, mount_path="", streamable_http_path="/mcp")

        assert server.settings.port == 0
        assert server.settings.mount_path == ""
        assert server.settings.streamable_http_path == "/mcp"

    def test_streamable_http_app_honors_mount_path(self):
        """Test ASGI helper mounts Streamable HTTP under the configured prefix."""
        streamable_app = create_streamable_http_app(
            mount_path="/clinic",
            streamable_http_path="/api/mcp",
        )

        mount = next(
            route for route in streamable_app.routes if route.path == "/clinic"
        )

        assert isinstance(mount, Mount)
        assert isinstance(mount.app, Starlette)
        assert any(route.path == "/api/mcp" for route in mount.app.routes)

    def test_mounted_streamable_http_app_runs_session_lifespan(self):
        """Mounted ASGI helper must start the FastMCP streamable session manager."""
        streamable_app = create_streamable_http_app(
            mount_path="/clinic",
            streamable_http_path="/api/mcp",
        )

        with TestClient(streamable_app, raise_server_exceptions=False) as client:
            response = client.get("/clinic/api/mcp")

        assert response.status_code < 500

    def test_main_uses_cli_sse_transport_options(self, monkeypatch):
        """Test CLI SSE options are forwarded to the server factory and runner."""
        captured: dict[str, object] = {}

        class FakeServer:
            def run(self, *, transport: str, mount_path: str | None = None) -> None:
                captured["transport"] = transport
                captured["mount_path"] = mount_path

        fake_server = FakeServer()

        def fake_create_server(**kwargs: object) -> FakeServer:
            captured["kwargs"] = kwargs
            return fake_server

        monkeypatch.setattr(server_module, "create_server", fake_create_server)

        server_module.main(
            [
                "--transport",
                "sse",
                "--host",
                "0.0.0.0",
                "--port",
                "9000",
                "--mount-path",
                "/clinic",
                "--streamable-http-path",
                "/api/mcp",
                "--stateless-http",
            ]
        )

        assert captured["kwargs"] == {
            "host": "0.0.0.0",
            "port": 9000,
            "mount_path": "/clinic",
            "streamable_http_path": "/api/mcp",
            "stateless_http": True,
        }
        assert captured["transport"] == "sse"
        assert captured["mount_path"] == "/clinic"

    def test_main_runs_streamable_http_through_mounted_asgi_helper(self, monkeypatch):
        """Streamable HTTP CLI path uses the ASGI helper so mount_path is honored."""
        captured: dict[str, object] = {}

        def fake_run_streamable_http_app(**kwargs: object) -> None:
            captured["kwargs"] = kwargs

        monkeypatch.setattr(
            server_module,
            "run_streamable_http_app",
            fake_run_streamable_http_app,
        )

        server_module.main(
            [
                "--transport",
                "streamable-http",
                "--host",
                "0.0.0.0",
                "--port",
                "9000",
                "--mount-path",
                "/clinic",
                "--streamable-http-path",
                "/api/mcp",
                "--stateless-http",
            ]
        )

        assert captured["kwargs"] == {
            "host": "0.0.0.0",
            "port": 9000,
            "mount_path": "/clinic",
            "streamable_http_path": "/api/mcp",
            "stateless_http": True,
        }

    def test_help_does_not_initialize_runtime_cache(self, tmp_path):
        """CLI help should not create cache or service state in the working dir."""
        result = subprocess.run(
            [sys.executable, "-m", "pharmacy_mcp", "--help"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        )

        assert "Run the Pharmacy MCP server." in result.stdout
        assert not (tmp_path / ".cache").exists()
