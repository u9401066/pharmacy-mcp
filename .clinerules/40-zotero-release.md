---
paths:
  - "pyproject.toml"
  - "src/pharmacy_mcp/__init__.py"
  - "uv.lock"
  - "README.md"
  - "README.zh-TW.md"
  - "CHANGELOG.md"
  - ".github/workflows/**"
---

# Pharmacy MCP Release Rules

These release rules apply to this Python package repository. Older Zotero
Keeper VSIX release commands are external-reference only and must not be run
from this workspace unless the referenced extension repository is open.

## Version Sources

- Python package metadata: `pyproject.toml`
- Python runtime fallback: `src/pharmacy_mcp/__init__.py`
- Changelog: `CHANGELOG.md`
- Lockfile: `uv.lock`

## Minimum Verification

- `uv run pytest --cov=src --cov-report=term-missing`
- `uv run ruff check src tests scripts`
- `uv run mypy src`
- `uv run bandit -q -r src`
- `uv build`
- `uv run python scripts/audit_release_artifacts.py dist`
- `git diff --check`

## Packaging Requirements

- Remove stale `dist/` contents before building a release.
- Confirm the artifact audit validates package name, version, required data
  files, archive size, and forbidden local/harness paths.
- Do not publish source distributions containing `.cache`, `.uv-cache`,
  assistant runtime state, virtual environments, or generated data exports.

## Tag Format

- Runtime package release tags use `vX.Y.Z`.
- Push the release commit before pushing the tag.
