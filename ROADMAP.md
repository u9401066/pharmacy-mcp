# Roadmap

## Released

### v0.9.0 - Trusted Formula And Simulation Modernization

- [x] Trusted PK/DDI formula catalog with auditable metadata.
- [x] Formula loader and domain value objects.
- [x] PBPK-lite simulation service for deterministic PK/DDI estimates.
- [x] Mechanism-aware interaction simulation for selected CYP inhibition pairs.
- [x] FastMCP tools, resources, resource templates, and prompts.
- [x] Streamable HTTP deployment helper.
- [x] Assistant harness assets documented for Codex, Claude, Cline, PubMed/Zotero, and Asset-Aware MCP workflows.
- [x] Release CI workflow with tests, coverage, ruff, mypy, bandit, and build.

### v0.8.0 - Taiwan TFDA/NHI Integration

- [x] TFDA search client and tools.
- [x] NHI coverage and reimbursement helpers.
- [x] English/Traditional Chinese drug-name mapping.
- [x] Taiwan-specific `DrugInfoService` integration.
- [x] Prior authorization and coverage-rule tools.

### v0.1.x - Core Pharmacy MCP

- [x] Project scaffold and packaging.
- [x] Drug, interaction, dosage, and order domain models.
- [x] Drug search and information services.
- [x] Dosing calculators.
- [x] Local interaction database after RxNorm interaction API discontinuation.

## Next

### v0.10.0 - Formula Authoring Harness

- [ ] Add an optional external-MCP harness for NSForge-style symbolic derivation and dimensional checks.
- [ ] Add a draft formula import workflow that stores generated formulas as untrusted review artifacts.
- [ ] Add formula promotion checks: references, unit review, numeric validation, tests, and safety text.
- [ ] Add formula diff reports for catalog review.
- [ ] Add more CYP, transporter, renal, and protein-binding examples with citations.

### v0.11.0 - Clinical Workflow Hardening

- [ ] Improve external API client typing and remove gradual mypy overrides module by module.
- [ ] Add structured error codes across all MCP tools.
- [ ] Add integration tests for Streamable HTTP.
- [ ] Add cache observability and explicit TTL configuration.
- [ ] Add richer provenance fields for FDA, RxNorm, TFDA, and NHI responses.

### v1.0.0 - Production Stabilization

- [ ] No known high-severity security issues.
- [ ] Strict typing on the actively maintained core and API boundaries.
- [ ] 80%+ coverage target after legacy API client cleanup.
- [ ] Complete user-facing documentation and examples.
- [ ] PyPI release workflow.
- [ ] Signed release artifacts and changelog automation.

## Non-Goals For 0.9.x

- No direct clinical recommendations from simulation outputs.
- No runtime execution of untrusted formula expressions.
- No vendored NSForge submodule unless a later release needs offline formula authoring.
- No commercial drug database integration without explicit licensing review.

*Last updated: 2026-05-17*
