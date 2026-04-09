"""Tests for MCP server."""

from starlette.applications import Starlette

from pharmacy_mcp.config import settings
from pharmacy_mcp.presentation import server as server_module
from pharmacy_mcp.presentation.server import (
    app,
    create_server,
    create_streamable_http_app,
)


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

        assert len(tools) == 25
        assert {
            "search_drug",
            "calculate_dose_by_weight",
            "search_tfda_drug",
            "validate_order",
            "submit_order",
            "stop_order",
        }.issubset(tool_names)

        search_tool = next(tool for tool in tools if tool.name == "search_drug")
        assert search_tool.inputSchema["properties"]["max_results"]["default"] == 10

    async def test_server_routes_structured_tool_calls(self):
        """Test registered FastMCP tools call the underlying services."""
        server = create_server()

        content, structured = await server.call_tool(
            "convert_dose_units",
            {"value": 1, "from_unit": "g", "to_unit": "mg"},
        )

        assert structured["converted_value"] == 1000
        assert structured["converted_unit"] == "mg"
        assert content[0].text

    def test_streamable_http_app_creation(self):
        """Test Streamable HTTP deployment helper returns an ASGI app."""
        streamable_app = create_streamable_http_app()

        assert isinstance(streamable_app, Starlette)
        assert isinstance(app, Starlette)
        assert any(route.path == settings.streamable_http_path for route in streamable_app.routes)

    def test_main_uses_cli_transport_options(self, monkeypatch):
        """Test CLI options are forwarded to the server factory and runner."""
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
        assert captured["transport"] == "streamable-http"
        assert captured["mount_path"] == "/clinic"
