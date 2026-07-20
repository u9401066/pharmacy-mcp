# Active Context

Updated: 2026-07-20

## Current objective

Finish the 1.0.0a1 modernization as a FastMCP + agent-harness single entry point
for pharmaceutical knowledge. Integrate the latest main-branch PK/DDI simulation
and HTTP deployment work without losing the stable output contract, Taiwan
compound queries, FHIR/inventory, organization connectors, CI, docs, or the
segmented release history.

## Integrated implementation state

- `PharmacyFastMCP` wraps all 33 tools in the strict seven-field
  `QueryResponse` v1.0 schema.
- Every tool accepts `output_format` and `locale`; deterministic text may be
  JSON, compact JSON, or Markdown while `structuredContent` is authoritative.
- The server supports stdio, SSE, Streamable HTTP, mounted ASGI, and lazy
  service/cache initialization.
- `query_pharmacy` routes public APIs, Taiwan sources, FHIR, SQL, vector,
  files, and fixed web sources with timeout and partial-failure isolation.
- Public sources include RxNorm/RxClass, all seven openFDA drug endpoints,
  DailyMed, PubChem, and MedlinePlus Connect.
- Taiwan queries combine TFDA permits, the official NHI monthly item index,
  price/ATC/effective dates, and coverage-rule metadata.
- FHIR R4/R5 supports medication/formulary, explicit patient order/dispense
  context, R5 inventory, and R4 supply fallback.
- Operator-bounded connectors cover PDF, DOC/DOCX, CSV, XLS/XLSX, Markdown,
  text, read-only SQLite, vector HTTP gateways, and fixed HTTPS documents.
- Trusted PK/DDI formulas, resources, validation fixtures, mechanism
  explanations, and fail-closed deterministic simulations are integrated.
- MkDocs/GitHub Pages, Python 3.11-3.13 CI, source-health checks, and release
  artifact audits are part of the release gate.

## Validation and release state

- Final integration audit passes 187 tests and 82.25% branch coverage, including
  ResourceWarning/PytestUnraisableExceptionWarning-as-error.
- Ruff format/check, repo-wide strict mypy, Bandit, strict MkDocs, lockfile,
  sdist/wheel, release-artifact audit, and isolated wheel CLI all pass.
- Installed-wheel MCP stdio passes with 33 tools, three prompts, compound query,
  and trusted simulation. A real Streamable HTTP client session also passes.
- All 14 official public API/dataset probes passed on 2026-07-20.
- Draft PR #2 targets `main` from
  `agent/modernize-unified-pharmacy-gateway`.
- Remote `main` advanced through 0.9.1 while this work was in progress. Its
  FastMCP/simulation work was integrated in an explicit two-parent merge.
- Remote integration commit `96447af9426b463c2104cc7d7f8fb67fc8158ffb`
  points to the exact locally audited tree, PR #2 is mergeable, and CI run
  29741488853 completed successfully.
- The local `gh` credential is invalid; the authenticated GitHub connector is
  used for publication without storing credentials in the repository.
- After owner-approved merge, repository Pages must use GitHub Actions.

## Immediate next actions

1. Review and merge PR #2 only with repository-owner approval.
2. Select GitHub Actions as the Pages source and verify the deployed site.
3. Re-authenticate terminal GitHub access before a future terminal-only push.
