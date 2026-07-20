# Roadmap

Updated: 2026-07-20

## v1.0.0a1 — unified pharmacy gateway

### Complete locally

- [x] Versioned `QueryResponse` schema and deterministic output renderers
- [x] MCP, Python harness, and CLI share one query contract
- [x] Capability/source routing with timeout and partial-failure isolation
- [x] RxNorm and structured RxClass execution
- [x] All seven openFDA drug endpoints with bounded projections
- [x] DailyMed, PubChem, and MedlinePlus Connect adapters
- [x] TFDA permits plus official NHI CSV → atomic SQLite index
- [x] Compound TFDA/NHI item/coverage queries
- [x] Read-only FHIR R4/R5 medication, order, dispense, inventory, and supply
- [x] PDF/DOC/DOCX/CSV/XLS/XLSX/Markdown/text, SQLite, vector, and web connectors
- [x] GitHub Pages documentation, multi-version CI, and weekly source-health probes
- [x] Strict Ruff, mypy, Bandit, branch coverage, package, docs, CLI, and MCP smoke gates
- [x] FastMCP stdio, SSE, Streamable HTTP, and lazy ASGI deployment
- [x] Trusted PK/DDI formula catalog, deterministic simulation, and validation resources

### Release boundary

- [x] Publish the segmented feature branch to GitHub
- [x] Integrate current main and verify a conflict-free PR with passing CI
- [ ] Review and merge through the repository's normal branch policy
- [ ] Select GitHub Actions as the repository Pages source
- [ ] Run the public-source workflow and verify the deployed documentation URL

The branch was published through the installed GitHub connector because the
machine-local `gh` credential was invalid. Re-authenticate `gh` before the next
terminal-only push; no credential was written into the repository.

## v1.0 prerelease — production hardening

- [ ] Add operator-configured SMART Backend Services token acquisition/rotation
- [ ] Add PostgreSQL and organization-specific SQL mapping adapters
- [ ] Add observable metrics/tracing without logging patient context or secrets
- [ ] Add configurable provider concurrency/rate limits and circuit breakers
- [ ] Add signed source snapshots and dataset freshness policies
- [ ] Add institution-specific FHIR conformance fixtures and inventory mappings

## v1.0.0 — stable contract

- [ ] Freeze and publish the v1 response/support policy
- [ ] Reach at least 80% branch coverage without excluding gateway paths
- [ ] Complete independent clinical-safety and threat-model review
- [ ] Publish deployment runbooks and container artifacts
- [ ] Publish the package after release-candidate interoperability testing

## Deliberate boundaries

- Licensed clinical knowledge (DrugBank, FDB, Micromedex) remains catalog-only
  until an operator supplies a valid contract, credentials, and adapter.
- The retired RxNorm interaction API is not emulated as an official service.
- Public/open datasets remain reference material, not a validated clinical
  decision-support engine.
- Write operations against hospital FHIR/HIS remain outside the unified
  knowledge-query provider unless explicitly designed and authorized later.
