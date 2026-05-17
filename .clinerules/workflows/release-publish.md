# Pharmacy MCP Release Publish

1. Update `pyproject.toml`, `src/pharmacy_mcp/__init__.py`, `uv.lock`, and
   `CHANGELOG.md`.
2. Clear `dist/`, build, and audit artifacts:

```bash
uv build
uv run python scripts/audit_release_artifacts.py dist
```

3. Run the full local gate from `.clinerules/workflows/full-check.md`.
4. Commit, push the release branch, tag as `vX.Y.Z`, and publish the GitHub
   release with the audited wheel and sdist.

No VSIX or npm release step applies to this repository.
