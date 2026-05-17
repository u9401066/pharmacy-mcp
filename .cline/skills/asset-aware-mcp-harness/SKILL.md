---
name: asset-aware-mcp-harness
description: "Cline harness for this repo (rules + workflows + checks). Triggers: cline harness, full check, release checklist, workflow, 文檔工作流, DFM, citation-ready."
---

# Asset-Aware Reference: Cline Harness Skill

Use this skill when working with bundled Asset-Aware reference workflows. This
repository is Pharmacy MCP, so extension-specific Asset-Aware commands are
external-reference only unless that repository is explicitly opened.

## What To Use First
- Rules: `.clinerules/` (always-on, with conditional scopes)
- Workflows: `.clinerules/workflows/`
  - Run `/full-check.md` for the full local gates
  - Run `/release-publish.md` for a guided tagged release
- Skills: this repo already has multiple skills under `.claude/skills/` (Cline can load them too)
  - If any `.claude/skills` instruction conflicts with current repo behavior, treat `.clinerules/` as the source of truth.

## Canonical Commands
- Tests: `uv run pytest --cov=src --cov-report=term-missing`
- Lint: `uv run ruff check src tests scripts`
- Type check: `uv run mypy src`
- Security scan: `uv run bandit -q -r src`
- Build: `uv build`
- Artifact audit: `uv run python scripts/audit_release_artifacts.py dist`

## Citation-Ready Mindset
- Prefer stable, verifiable spans (line/char/byte offsets + hashes) over loose “source: page 3” citations.
- Treat CRAAP fields as a conservative scaffold: avoid claiming more confidence than you can actually verify.

## MCP Auto-Config Mindset
- Preserve unrelated MCP servers and user-local Cline/Codex metadata.
- Do not run VSIX or extension setup from this repository unless the external
  extension workspace is open.
