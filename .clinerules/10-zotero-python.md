# Legacy Zotero Python Rules

This file is retained only as a bundled harness marker. The current Pharmacy
MCP repository has no `mcp-server/` layout. Do not run Zotero Keeper Python
commands here unless an external Zotero Keeper repository is explicitly opened.

For this repository, use:

- `uv run pytest --cov=src --cov-report=term-missing`
- `uv run ruff check src tests scripts`
- `uv run mypy src`
