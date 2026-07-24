# Contributing

Contributions are welcome for adapters, data-quality fixes, tests, and
documentation. For clinical content, include a primary/official source and make
the effective date and jurisdiction explicit.

## Local setup

```bash
git clone https://github.com/u9401066/pharmacy-mcp.git
cd pharmacy-mcp
uv sync --all-extras
```

Use a focused branch and Conventional Commits (`feat:`, `fix:`, `docs:`,
`refactor:`, `test:`, `chore:`). Keep unrelated changes in separate commits.

## Required checks

```bash
uv run pytest
uv run ruff check src tests examples
uv run mypy src
uv run mkdocs build --strict
```

Network-dependent checks must be explicit integration tests; the default suite
must use synthetic fixtures or mocked transports. Never place credentials or
patient data in a test.

## Adding a provider

1. Add an honest `ProviderDescriptor` to the catalog, including capabilities,
   credential needs, documentation, and implementation state.
2. Implement the `KnowledgeProvider` port with bounded output and provenance.
3. Register it only when all required settings are present.
4. Isolate timeouts/errors and do not silently substitute another authority.
5. Test success, malformed upstream data, failure, secret boundaries, and any
   patient or data-egress behavior.
6. Update `docs/data-sources.md`, relevant setup docs, `.env.example`,
   `CHANGELOG.md`, and the Memory Bank.

Licensed sources must not be scraped, reverse engineered, or described as
enabled without an organization's valid agreement and credentials.

## Changing output

`QueryResponse` is an external compatibility contract. Preserve its seven
top-level fields and `additionalProperties: false`. A breaking meaning or shape
change requires a new schema version, migration notes, renderer updates, MCP
`outputSchema` tests, harness tests, and changelog documentation.

## Pull requests

Explain the user-facing outcome, source/legal assumptions, security or clinical
risk, verification performed, and documentation changes. Small reviewable
commits are preferred. CI must pass and review discussion should be resolved
before merge. Participation follows [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
