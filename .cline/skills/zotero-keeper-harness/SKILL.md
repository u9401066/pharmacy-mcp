---
name: zotero-keeper-harness
description: "Cline harness for Zotero/PubMed assistant workflows bundled with Pharmacy MCP. Triggers: zotero keeper, zotero mcp, full check, release checklist, workflow, Cline."
---

# Zotero Keeper: Cline Harness Skill

Use this skill when working in this repository with Cline and you need the reliable loop:
understand the Zotero/PubMed boundary, make a scoped change, and verify Pharmacy
MCP. Extension-specific Zotero Keeper commands are legacy reference material
unless an external extension repository is explicitly opened.

## What To Use First

- Rules: `.clinerules/`
- Workflows: `.clinerules/workflows/`
  - Run `/zotero-full-check.md` for local gates.
  - Treat extension release workflows as legacy unless the referenced paths exist.
  - Run `/zotero-skills-audit.md` after changing skills or rules.
- Existing skills: `.claude/skills/`
  - If a `.claude/skills` instruction conflicts with current repo behavior, prefer `.clinerules/`.

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
- Do not bypass the NCBI email policy; use explicit settings or the git email fallback.
- Do not run `npm`, VSIX, `mcp-server/`, `vscode-extension/`, or
  `external/pubmed-search-mcp/` commands from this repository unless those paths
  exist in the active workspace.
