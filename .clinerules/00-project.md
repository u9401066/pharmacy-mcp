# Pharmacy MCP Core Rules

This repository is the Pharmacy MCP Python package. Extension, VSIX, Zotero
Keeper, PubMed Search MCP, and Asset-Aware commands in legacy bundled harness
assets are external-reference only unless those repositories are explicitly
opened in the active workspace.

Use the current repository gates:

- `uv run pytest --cov=src --cov-report=term-missing`
- `uv run ruff check src tests scripts`
- `uv run mypy src`
- `uv run bandit -q -r src`
- `uv build`
- `uv run python scripts/audit_release_artifacts.py dist`
- `git diff --check`
