# Pharmacy MCP Project Rules

These Cline rules are bundled harness assets for Pharmacy MCP. Zotero Keeper
and VS Code extension commands from older harnesses are external-reference only
unless the corresponding external repository is explicitly opened.

## Goals

- Maintain a Python MCP server for medication reference workflows.
- Keep PubMed/Zotero assistant workflows as optional harness assets, not runtime
  package dependencies.
- Preserve research safety: ask before importing into Zotero collections, avoid
  duplicates, and keep source metadata traceable.

## Repo Layout

- `src/pharmacy_mcp/`: runtime package code.
- `tests/`: unit and service tests.
- `.codex/`, `.claude/`, `.cline/`, `.clinerules/`: assistant harness assets.
- `.github/`: CI workflows, agents, hooks, and policy docs.

## Canonical Commands

- Tests: `uv run pytest --cov=src --cov-report=term-missing`
- Lint: `uv run ruff check src tests scripts`
- Type check: `uv run mypy src`
- Security scan: `uv run bandit -q -r src`
- Build: `uv build`
- Artifact audit: `uv run python scripts/audit_release_artifacts.py dist`
- Diff hygiene: `git diff --check`

## Safety / Hygiene

- Avoid editing generated outputs: `dist/`, `.venv/`, `.pytest_cache/`,
  `.ruff_cache/`, `.mypy_cache/`, `.cache/`, `__pycache__/`.
- Never print or commit secrets, PHI, NCBI API keys, Zotero credentials, or key
  files.
- Do not use destructive git commands unless the user explicitly asks.
- Do not run `npm`, VSIX, `mcp-server/`, `vscode-extension/`, or
  `external/pubmed-search-mcp/` commands from this repository unless those paths
  exist in the active workspace.

## Prefer Existing Patterns

- Keep MCP tool outputs backward-compatible when possible.
- Keep formulas data-first: trusted catalog metadata plus reviewed Python
  implementations, not arbitrary expression execution.
- Keep clinical outputs non-prescriptive and include safety metadata.
