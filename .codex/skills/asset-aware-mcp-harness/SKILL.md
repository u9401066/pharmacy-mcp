---
name: asset-aware-mcp-harness
description: "Codex harness for Asset-Aware MCP references bundled with Pharmacy MCP. Triggers: asset-aware, MCP, PDF, DOCX, DFM, citation-ready, CRAAP, release checklist."
---

# Asset-Aware MCP: Codex Harness Skill

Use this skill when working with Codex on Asset-Aware MCP reference workflows
bundled in this repository. Extension-specific commands are external-reference
only unless the referenced extension repository is explicitly opened.

## What To Read First

- `AGENTS.md` for Codex workspace instructions.
- `.github/copilot-instructions.md` for cross-agent project guardrails.
- `.clinerules/` for implementation and release rules that also apply here.
- `memory-bank/activeContext.md` for the current working focus.

## Canonical Commands

- Tests: `uv run pytest --cov=src --cov-report=term-missing`
- Lint: `uv run ruff check src tests scripts`
- Type check: `uv run mypy src`
- Security scan: `uv run bandit -q -r src`
- Build: `uv build`
- Artifact audit: `uv run python scripts/audit_release_artifacts.py dist`

## Citation-Ready Rules

- Prefer verifiable spans: source revision, span IDs, byte/char/line offsets,
  context text, and hashes.
- Keep CRAAP values conservative unless the implementation can justify them.
- Preserve aliases/backward compatibility when evolving MCP tool payloads.

## Release Rules

- Do not run extension, VSIX, Docker, or Asset-Aware package release commands
  from Pharmacy MCP unless that external repository is active.
- Do not tag until tests, lint, type checks, security scan, package build,
  artifact audit, wheel smoke, and git diff hygiene are clean.
