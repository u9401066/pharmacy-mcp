# Pharmacy MCP Release Rules

This repository releases a Python package, not a VS Code extension.

Release gates:

- `uv run pytest --cov=src --cov-report=term-missing`
- `uv run ruff check src tests scripts`
- `uv run mypy src`
- `uv run bandit -q -r src`
- `uv build`
- `uv run python scripts/audit_release_artifacts.py dist`
- `git diff --check`

Release artifacts must be built from a clean `dist/` directory and audited for
package name, version, size, required data files, and forbidden cache/harness
paths.
