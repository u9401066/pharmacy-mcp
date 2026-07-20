# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Added the `QueryResponse` v1.0 envelope to every FastMCP tool, with
  deterministic JSON, compact JSON, and Markdown renderings.
- Added `query_pharmacy`, `list_knowledge_sources`, `get_nhi_data_status`, the
  Python harness/CLI, and the `pharmacy-query-contract` prompt.
- Added capability-routed providers for RxNorm/RxClass, all seven openFDA drug
  endpoints, DailyMed, PubChem, MedlinePlus Connect, PubMed,
  ClinicalTrials.gov, ChEMBL, Open Targets, TFDA/NHI, FHIR R4/R5, local files,
  SQLite, vector gateways, and fixed HTTPS documents.
- Added an atomic official NHI CSV index and compound TFDA/NHI coverage queries.
- Added MkDocs/GitHub Pages deployment and a weekly 18-surface source probe.

### Changed
- Integrated the 0.9.1 FastMCP transports and trusted PK/DDI simulation catalog
  into the unified gateway without weakening its output contract.
- Set the package prerelease version to `1.0.0a1`.
- Restored repo-wide strict mypy, Ruff, Bandit, coverage, package, docs, CLI,
  MCP transport, and release-artifact gates.

### Fixed
- Fixed current TFDA HTTPS ZIP ingestion, nullable fields, NHI ROC-date
  comparisons, provider partial-status propagation, explicit resource
  lifecycles, and import-time Taiwan cache creation.

---

## [0.9.1] - 2026-05-17

### Added
- Added release artifact auditing for wheel/sdist contents, size limits, and bundled runtime data files.
- Added packaged-wheel smoke testing in CI.

### Changed
- Hardened interaction outputs with non-prescriptive safety language and explicit clinical-decision disclaimers.
- Made MCP server services and the Streamable HTTP ASGI export lazy to avoid import-time runtime cache creation.
- Tightened trusted formula catalog validation for duplicate IDs, provenance, validation cases, and supported implementation keys.
- Added bounded runtime dependency ranges and pinned the build backend major version.

### Fixed
- Fixed multi-drug interaction sorting for FDA-only interaction hits.
- Fixed PK simulation fail-closed handling for NaN, infinity, unstable denominators, and nested simulation errors.
- Fixed Streamable HTTP ASGI helper mounting so non-root `mount_path` prefixes are honored.
- Excluded local caches, assistant harness assets, and generated runtime folders from source distributions.
- Removed a Taiwan drug service singleton that created `.cache` during `python -m pharmacy_mcp --help`.

---

## [0.9.0] - 2026-05-17

### Added
- Added a trusted PK/DDI formula catalog at `src/pharmacy_mcp/data/formulas/trusted_pk_ddi.json`.
- Added formula metadata value objects and catalog loader with references, assumptions, limitations, parameters, and validation cases.
- Added `SimulationService` for PBPK-lite deterministic calculations:
  - one-compartment concentration-time estimates
  - repeated-dose accumulation factor
  - renal clearance adjustment
  - CYP reversible inhibition clearance and AUC ratio
  - temperature-corrected elimination rate
- Added mechanism-aware DDI simulation support for selected CYP inhibition examples.
- Added MCP tools:
  - `list_formula_catalog`
  - `get_formula_details`
  - `explain_interaction_mechanism`
  - `simulate_pk_interaction`
  - `simulate_concentration_time`
- Added MCP resources and templates:
  - `pharmacy://server/disclaimer`
  - `pharmacy://formulas`
  - `pharmacy://formulas/{formula_id}`
  - `pharmacy://validation/formulas`
- Added MCP prompts:
  - `ddi_analysis_workflow`
  - `formula_review_checklist`
- Added release CI workflow covering pytest coverage, ruff, mypy, bandit, and package build.
- Added deterministic service path tests for drug search, drug info, interaction lookup, server routing, formula catalog, and simulation.

### Changed
- Upgraded package metadata to 0.9.0 and raised the MCP SDK lower bound to `mcp>=1.27.0`.
- Replaced MD5-derived cache keys with SHA-256.
- Reformatted source and tests with ruff.
- Rewrote README files to list the actual 0.9.0 MCP tools and safety model.
- Documented NSForge as an external formula-authoring companion rather than a vendored dependency.
- Made mypy release-gate friendly: new formula/simulation code remains strict, while inherited external API/service modules use explicit gradual-typing overrides.

### Fixed
- Removed outdated README tool names that did not match the registered FastMCP server.
- Restored coverage gate to 70% with focused non-network tests.

---

## [0.8.0] - 2025-12-22

### Added
- Added Taiwan TFDA drug search support.
- Added Taiwan NHI coverage and reimbursement helpers.
- Added Traditional Chinese and English drug-name translation helpers.
- Added prior authorization and NHI coverage rule tools.
- Added `TaiwanDrugService`.

### Changed
- Extended `DrugInfoService.get_full_info()` with Taiwan-specific information.

---

## [0.1.1] - 2025-12-22

### Fixed
- Replaced the discontinued RxNorm Drug Interaction API path with a local interaction database and FDA label context.

### Changed
- Updated interaction outputs with source and note fields to clarify data provenance.

---

## [0.1.0] - 2025-12-22

### Added
- Initial project scaffold.
- Core domain models.
- Drug search, drug info, dosage, interaction, and food-drug interaction tool foundations.
- Python packaging and initial README files.
