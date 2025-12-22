"""Tests for MCP server."""

import pytest

from pharmacy_mcp.presentation.server import create_server


class TestMCPServer:
    """Tests for MCP server."""
    
    @pytest.fixture
    def server(self):
        """Create server instance."""
        return create_server()
    
    def test_server_creation(self, server):
        """Test server can be created."""
        assert server is not None
        assert server.name == "pharmacy-mcp"
