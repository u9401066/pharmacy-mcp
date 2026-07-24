# Active Context

Updated: 2026-07-24

## Current objective

The post-merge 1.0.0a1 gateway modernization is complete on the isolated
`agent/modernize-pharmacy-mcp-readme` branch. The branch is published as
segmented feature, test, documentation, and Memory Bank commits while private
organization contracts and pre-existing harness edits remain local-only.

## Integrated implementation state

- PR #2 was merged into `main`; local `main` and `origin/main` were synchronized
  before this phase began.
- `PharmacyFastMCP` exposes 35 tools through strict `QueryResponse` v1.0.
- `query_pharmacy` resolves capability-compatible providers, rejects fan-out
  above the operator budget, bounds simultaneous provider execution, applies
  per-provider timeouts, and preserves partial success and provenance.
- Public providers cover RxNorm/RxClass, seven openFDA drug surfaces, DailyMed,
  PubChem, MedlinePlus, PubMed, ClinicalTrials.gov, ChEMBL, and Open Targets.
- Taiwan queries combine TFDA permits, official NHI monthly data, price/ATC/
  effective dates, and coverage-rule metadata.
- FHIR R4/R5 is read-only and preserves raw standard fields, extensions,
  profiles, and hospital-defined keys. Search Bundle/resource types are checked,
  and `inspect_fhir_server` projects the live CapabilityStatement safely.
- File search covers PDF, DOC/DOCX, CSV, XLS/XLSX, Markdown, and text. Results
  include opaque document IDs, extracted-text SHA-256 revisions, and exact
  line/character locators; `read_knowledge_document` performs bounded ID-only
  retrieval without accepting paths.
- SQLite remains `mode=ro` with administrator allowlisted tables/columns and
  bound query values. Vector and fixed-web connectors retain their explicit
  outbound-data and SSRF boundaries.
- The private SOAP/WCF contract was inspected locally and implemented as the
  configurable `wcf` provider. Real URL/action/field names live only in ignored
  `.env`; repository examples are generic. The provider uses TLS by default,
  defused XML, byte/record limits, a TTL snapshot cache, and output allowlists.
- The two private internal API archives remain exactly ignored and untracked;
  neither archive nor extracted source is copied into code, tests, docs, build,
  staging, or publication artifacts.

## Current validation state

- Full suite: 206 tests passed with 83.46% branch coverage (70% gate).
- Repo-wide Ruff format/check, strict mypy, and Bandit pass.
- Lockfile check and strict MkDocs build pass.
- sdist/wheel build, release-artifact audit, private-contract scan, and ignored/
  untracked Git checks pass.
- Python 3.13 isolated wheel smoke confirms the built package (not the source
  checkout) exposes 35 schema-bearing MCP tools.
- The redesigned English/Traditional Chinese READMEs now embed two accessible,
  repo-native SVGs and Mermaid diagrams for provider fan-out, FHIR compatibility,
  and citation-ready document retrieval.
- `architect.md` and `systemPatterns.md` now describe the 35-tool schema-bound
  gateway instead of the historical 19-tool design.
- Post-document verification passes: SVG XML/render inspection, 206 tests,
  83.46% branch coverage, Ruff format/check, strict mypy, Bandit, lock check,
  MkDocs strict, sdist/wheel audit, and isolated Python 3.13 35-tool wheel smoke.
- Tracked source and both release artifacts have zero matches for the private
  WCF contract identifiers; `.env` and both private archives remain exact-ignore.
- The live WCF host resolves to an internal address but is not reachable from
  this execution environment. The provider reports an isolated retryable error;
  its SOAP contract, cache, bounds, and projection are covered by mock tests.

## Publication checkpoint

- Branch: `agent/modernize-pharmacy-mcp-readme`
- `01228f8` — bounded provider execution, FHIR/document access, generic WCF
- `36361c4` — connector, FHIR, server, and fan-out regression coverage
- `024f954` — bilingual README, SVG/Mermaid, architecture, and connector docs
- Final segment — this Memory Bank checkpoint
- Remote: `origin/agent/modernize-pharmacy-mcp-readme`

## Immediate next actions

1. Review and merge the published branch when repository-owner approval is given.
2. Run one live `source=wcf` query from a host on the hospital network.
3. Keep future FHIR profile-specific mappings additive and organization-owned.
