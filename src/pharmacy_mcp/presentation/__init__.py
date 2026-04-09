"""Presentation layer - MCP Server and deployment helpers."""

from pharmacy_mcp.presentation.server import (
    app,
    create_server,
    create_streamable_http_app,
    main,
)

__all__ = ["app", "create_server", "create_streamable_http_app", "main"]
