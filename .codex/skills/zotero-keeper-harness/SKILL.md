---
name: zotero-keeper-harness
description: "Codex harness for Zotero/PubMed assistant workflows bundled with Pharmacy MCP. Triggers: zotero keeper, zotero mcp, full check, release checklist, workflow, Codex."
---

# Zotero Keeper: Codex Harness Skill

Use this skill when working with Codex on the installed Zotero + PubMed MCP
workspace harness. In this repository, treat extension-specific Zotero Keeper
commands as legacy reference material unless an external extension repository is
explicitly opened.

## What To Read First

- `AGENTS.md` for Codex workspace instructions.
- `.github/zotero-research-workflow.md` for the end-user research flow.
- `.clinerules/` for repo and release guardrails that also apply to Codex.
- `.claude/skills/pubmed-*` for user-facing research skills.

## Pharmacy MCP Canonical Commands

- Tests: `uv run pytest --cov=src --cov-report=term-missing`
- Lint: `uv run ruff check src tests scripts`
- Type check: `uv run mypy src`
- Security scan: `uv run bandit -q -r src`
- Build: `uv build`
- Artifact audit: `uv run python scripts/audit_release_artifacts.py dist`

## Product Guardrails

- Keep Zotero local-library behavior separate from PubMed literature-search behavior.
- Use `import_articles` as the preferred bridge from PubMed results/RIS into Zotero.
- Do not bypass NCBI email policy; use explicit settings or git email fallback.
- Do not run `npm`, VSIX, `mcp-server/`, `vscode-extension/`, or
  `external/pubmed-search-mcp/` commands from this repository unless those paths
  exist in the active workspace.
