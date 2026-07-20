# Pharmacy MCP Full Check

Run these commands from the repository root:

```bash
uv run pytest --cov=src --cov-report=term-missing
uv run ruff check src tests scripts
uv run mypy src
uv run bandit -q -r src
uv build
uv run python scripts/audit_release_artifacts.py dist
git diff --check
```

Do not run npm, VSIX, or extension commands from this repository unless an
external extension workspace is explicitly open.
