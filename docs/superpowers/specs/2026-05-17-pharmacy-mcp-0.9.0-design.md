# Pharmacy MCP 0.9.0 Design

## Goal

Release Pharmacy MCP 0.9.0 as a production-leaning MCP server with a trusted PK/DDI formula catalog, simulation-backed interaction tools, modern MCP surfaces, assistant harness assets, and green local/CI verification.

## Scope

0.9.0 adds a PBPK-lite layer. It does not claim to be a full PBPK engine and does not make clinical treatment decisions. The release focuses on deterministic formulas, explicit assumptions, source provenance, and validation fixtures that can be audited.

Included:

- Trusted Formula Catalog stored in repository data files.
- Formula loader and evaluator with unit-aware metadata and explicit trust status.
- PK/DDI simulation service for reversible CYP inhibition, renal clearance adjustment, one-compartment concentration-time, and repeated dosing summaries.
- New MCP tools for mechanism explanation, formula listing, formula inspection, and simulation.
- MCP resources/prompts that expose formula metadata and standard DDI analysis workflows.
- Harness assets for Codex, Claude, Cline, GitHub agents, and MCP workflows.
- Version, changelog, README, roadmap, and CI updates for 0.9.0.

Deferred to 0.10.0:

- NSForge vendoring or submodule integration.
- Runtime promotion of generated formulas into trusted status.
- OSP Suite or full PBPK backend integration.
- Commercial database integrations.

## Architecture

The existing DDD layering remains. The new formula capability lives in infrastructure/data plus application services:

- `domain/value_objects/formula.py`: immutable formula metadata and simulation result objects.
- `infrastructure/knowledge/formula_catalog.py`: loads trusted formula YAML/JSON data and validates metadata.
- `application/services/simulation.py`: deterministic PK/DDI calculations using trusted formulas.
- `application/services/interaction.py`: keeps current local/FDA lookup behavior and adds mechanism-aware simulation support through the new service.
- `presentation/server.py`: exposes tools, resources, and prompts through FastMCP.

The catalog is data-first. Formula expressions are not arbitrary runtime code. The evaluator dispatches by formula ID to reviewed Python implementations so formula metadata can be safely exposed without executing untrusted expressions.

## Formula Trust Model

Each formula has:

- `id`, `name`, `version`, and `status`.
- `expression` for human audit.
- `parameters` with units and descriptions.
- `assumptions`, `limitations`, and `references`.
- `validation_cases` with expected numeric ranges.

Trusted formulas are committed, tested, and versioned. Draft formulas from NSForge or another external MCP may be documented as provenance, but they cannot be used by production simulation tools until added to the trusted catalog and covered by tests.

## Initial Formulas

0.9.0 ships these core formula kernels:

- `one_compartment_concentration`: `C(t) = dose / Vd * exp(-ke * t)`
- `multiple_dose_accumulation`: `R = 1 / (1 - exp(-ke * tau))`
- `renal_clearance_adjustment`: `CL_adjusted = CL_nonrenal + CL_renal * renal_function_ratio`
- `cyp_reversible_inhibition_clearance`: `CL_inhibited = CL_total * ((1 - fm) + fm / (1 + I / Ki))`
- `auc_ratio_from_clearance`: `AUC_ratio = CL_baseline / CL_inhibited`
- `temperature_corrected_elimination`: `ke_adjusted = ke_ref * q10 ** ((temperature_c - reference_c) / 10)`

## MCP Surface

Tools:

- `list_formula_catalog`
- `get_formula_details`
- `explain_interaction_mechanism`
- `simulate_pk_interaction`
- `simulate_concentration_time`

Resources:

- `pharmacy://formulas`
- `pharmacy://formulas/{formula_id}`
- `pharmacy://validation/formulas`

Prompts:

- `ddi_analysis_workflow`
- `formula_review_checklist`

Structured outputs are dictionaries/Pydantic-compatible objects with deterministic keys. Medical disclaimer is included in simulation and interaction outputs.

## External MCP Harness

The repo includes assistant harness assets for PubMed Search MCP, Zotero Keeper, Asset-Aware MCP, and Codex/Claude/Cline workflows. NSForge is documented as an external companion MCP:

- Pharmacy MCP owns trusted formulas and clinical safety output.
- NSForge owns draft derivation, symbolic simplification, and dimensional checking.
- Promotion from draft to trusted requires review and tests.

## Validation

Release gates:

- `uv run pytest`
- `uv run pytest --cov=src --cov-report=term-missing`
- `uv run ruff check src tests`
- `uv run mypy src`
- `uv run bandit -q -r src`
- `uv build`

CI must run the same gates on Python 3.11 and 3.12 where practical. If strict mypy is too broad for inherited code, 0.9.0 may use targeted overrides with an explicit debt note, but new simulation code must be typed.

## Safety

Simulation tools return estimates, assumptions, limitations, confidence, and data gaps. They do not recommend starting, stopping, or changing therapy. Outputs always include the project disclaimer and mark PBPK-lite estimates as decision support only.
