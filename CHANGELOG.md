# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- None.

### Changed
- None.

### Fixed
- None.

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
