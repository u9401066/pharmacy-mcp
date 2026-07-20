# Active Context

Updated: 2026-07-20

## Current objective

Finish the v0.9.0a1 modernization as an MCP + agent-harness single entry point
for pharmaceutical knowledge, with stable output, Taiwan compound queries,
hospital FHIR/inventory, organization connectors, modern CI/docs, segmented
Git history, and a pushed remote branch.

## Local implementation state

- `QueryResponse` v1.0 fixes the seven top-level fields and rejects extras.
- Every MCP tool accepts `output_format`/`locale`, declares one output schema,
  and treats `structuredContent` as authoritative.
- `query_pharmacy` routes APIs/FHIR/SQL/vector/files/web through one provider
  port with concurrency, timeout, provenance, and partial-failure isolation.
- Public providers execute RxNorm, structured RxClass, all seven openFDA drug
  endpoints, DailyMed, PubChem, and MedlinePlus Connect.
- Taiwan compound queries combine TFDA permits, official NHI items/prices/ATC/
  effective dates, and coverage-rule metadata. The live NHI index contains
  224,455 source rows from the 2026-07-20 validation run.
- TFDA follows the current HTTPS ZIP distribution, enforces archive limits,
  accepts one JSON member, and remains compatible with legacy plain JSON.
- Read-only FHIR R4/R5 supports medication/formulary, explicit patient order and
  dispense context, R5 inventory, and R4 supply fallback.
- Operator-bounded connectors cover PDF, DOC/DOCX, CSV, XLS/XLSX, Markdown,
  text, read-only SQLite, vector HTTP gateways, and fixed HTTPS documents.
- Python `PharmacyHarness`, `pharmacy-query`, and MCP use the same contract.
- MkDocs/GitHub Pages, Python 3.11–3.13 CI, strict quality/security gates, and a
  weekly 14-surface public-source health workflow are present.

## Latest audit findings resolved

- Replaced the former `rxclass` alias with a real provider that retains class
  ID/type/relation/source.
- Replaced the label-only openFDA provider with capability routing for label,
  event, NDC, enforcement, Drugs@FDA, Orange Book, and shortages.
- Bounded large label and nested regulatory payloads before agent context.
- Propagated provider `partial` status through the top-level unified response.
- A live source-health run detected the retired TFDA redirect; the new ZIP
  ingestion fixed it, and all 14 live probes then passed.

## Validation and release state

- Final audit: 120 tests, 79.94% branch coverage, Ruff, strict mypy, Bandit,
  ResourceWarning-as-error, strict MkDocs, sdist/wheel, isolated CLI, and MCP
  stdio smoke all passed.
- Live official checks passed for all 14 health probes, all seven openFDA drug
  endpoints, structured RxClass, and the compound TFDA + NHI provider.
- Work is on `agent/modernize-unified-pharmacy-gateway` in segmented commits.
- External blocker: the local `gh` credential for `u9401066` is invalid, so an
  authenticated push cannot complete until the operator runs
  `gh auth login -h github.com`.
- After push/merge, repository Settings → Pages must use **GitHub Actions**.

## Immediate next actions

1. Attempt `git push --set-upstream origin agent/modernize-unified-pharmacy-gateway`.
2. If authentication still fails, preserve the exact recovery command for the operator.
3. After push/merge, enable GitHub Actions Pages and inspect the first workflows.
