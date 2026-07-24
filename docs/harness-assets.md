# Assistant Harness Assets

This repository bundles assistant-facing harness files so Codex, Claude, Cline,
GitHub agents, and external MCP workflows can work with the same project rules.

## Included Harness Areas

- `AGENTS.md`: workspace instructions for Codex and related coding agents.
- `.codex/skills/`: Codex skills for PubMed Search MCP, Zotero Keeper,
  Asset-Aware MCP, LLM wiki building, and academic figure workflows.
- `.claude/skills/`: Claude-oriented workflow skills and PubMed helper skills.
- `.cline/skills/` and `.clinerules/`: Cline workflow and release rules.
- `.github/agents/`: GitHub Copilot agent profiles for coding, review,
  research, orchestration, and test running.
- `.github/hooks/` and `scripts/hooks/`: policy and pipeline hook templates.
- `.asset-aware-mcp/assistant-assets.json`: Asset-Aware MCP manifest.

## External MCP Boundary

The 1.0 prerelease treats these integrations as harness assets, not runtime dependencies of
the pharmacy server. Pharmacy MCP can be installed and tested without Zotero,
PubMed Search MCP, Asset-Aware MCP, or NSForge running.

Runtime package code owns:

- MCP pharmacy tools, resources, prompts, and transports.
- Trusted formula catalog loading.
- Deterministic PBPK-lite simulation.
- Clinical safety wording and disclaimers.

Harness assets own:

- Agent workflow instructions.
- External research/import workflows.
- Document and citation preparation flows.
- Optional formula-authoring workflow guidance.

## NSForge Position

NSForge is best treated as an external companion for formula authoring:

- Use NSForge to draft expressions, simplify equations, or check dimensions.
- Do not execute NSForge-generated formulas directly inside Pharmacy MCP tools.
- Promote a formula only after review, source attribution, validation cases,
  committed catalog metadata, and tests.

The 1.0 prerelease intentionally does not add NSForge as a submodule or vendored dependency.
That keeps the runtime server smaller and makes the trusted formula boundary
auditable. A later release can add an optional `external-mcp/nsforge` harness if
the formula-promotion workflow needs tighter automation.

## Packaging Note

The workspace instructions mention `npm run sync-assets` for VSIX-oriented
projects. This repository currently has no `package.json` or VS Code extension
package, so that command is not a 1.0 release gate. CI instead validates the
Python package and checked-in harness assets with:

```bash
uv run pytest --cov=src --cov-report=term-missing
uv run ruff check src tests scripts
uv run mypy src
uv run bandit -q -r src
uv build
uv run python scripts/audit_release_artifacts.py dist
```

Hook state under `.github/hooks/_state/` is ignored, and hook audit logs should
store hashes/lengths rather than raw research prompts or queries. Do not place
PHI or secrets in research prompts.
