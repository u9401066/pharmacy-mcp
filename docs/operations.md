# Operations and source health

## Quality gates

Run the same local gates used by CI before release:

```bash
uv sync --locked --all-extras --dev
uv run ruff format --check src tests examples scripts
uv run ruff check src tests examples scripts
uv run mypy src
uv run bandit -r src -c pyproject.toml -q
uv run pytest --cov=pharmacy_mcp --cov-report=term
uv run mkdocs build --strict
uv build
```

## Public-source drift

`.github/workflows/source-health.yml` runs every Monday and can also be started
manually. It executes `scripts/check_source_health.py`, which concurrently
probes 14 surfaces:

- RxNorm and RxClass
- all seven openFDA drug endpoints
- DailyMed, PubChem, and MedlinePlus Connect
- TFDA and NHI official dataset download endpoints

The TFDA and NHI checks validate the response stream without consuming their
large dataset bodies. The command prints one machine-readable JSON report and
returns a non-zero exit status if any probe fails:

```bash
uv run python scripts/check_source_health.py
```

This is availability and API-drift monitoring, not a validation of clinical
content. Investigate a failure before changing query semantics or silently
substituting another source.

## Dataset refresh

The NHI index records source metadata and refresh time in its SQLite metadata
table. Use the MCP tool `get_nhi_data_status` before and after refresh. The
index is built in a temporary database and atomically replaces the prior usable
index only after validation succeeds.

TFDA publishes the permit datasets as ZIP-compressed JSON. The adapter accepts
exactly one JSON member, enforces an uncompressed-size ceiling, and caches the
validated records for seven days.

## GitHub Pages

The Pages workflow builds MkDocs in strict mode, uploads the official Pages
artifact, and deploys only from `main`. In repository Settings → Pages, select
**GitHub Actions** as the source after the first push.
