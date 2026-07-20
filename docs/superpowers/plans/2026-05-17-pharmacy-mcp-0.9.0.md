# Pharmacy MCP 0.9.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Implemented on the `release/0.9.0-simulation-modernization` branch.

**Goal:** Build and release Pharmacy MCP 0.9.0 with a trusted formula catalog, PBPK-lite simulation tools, modern MCP resources/prompts, harness assets, and green verification.

**Architecture:** Keep the existing DDD layers. Add formula metadata in repository data, a catalog loader in infrastructure, simulation orchestration in application services, and MCP tools/resources/prompts in presentation.

**Tech Stack:** Python 3.11+, FastMCP from the official MCP Python SDK, Pydantic/dataclasses, pytest, ruff, mypy, bandit, uv.

---

## File Structure

- Create `src/pharmacy_mcp/domain/value_objects/formula.py` for formula and simulation value objects.
- Create `src/pharmacy_mcp/infrastructure/knowledge/formula_catalog.py` for loading trusted formula data.
- Create `src/pharmacy_mcp/data/formulas/trusted_pk_ddi.json` for committed formula metadata.
- Create `src/pharmacy_mcp/application/services/simulation.py` for deterministic PK/DDI calculations.
- Modify `src/pharmacy_mcp/application/services/interaction.py` to expose mechanism explanations and simulation integration.
- Modify `src/pharmacy_mcp/presentation/server.py` to register new tools/resources/prompts.
- Add tests in `tests/test_formula_catalog.py`, `tests/test_simulation.py`, and extend `tests/test_server.py`.
- Add `.github/workflows/ci.yml`.
- Update `pyproject.toml`, `README.md`, `README.zh-TW.md`, `ROADMAP.md`, `CHANGELOG.md`, and `src/pharmacy_mcp/__init__.py`.

## Task 1: Trusted Formula Catalog

**Files:**
- Create: `src/pharmacy_mcp/domain/value_objects/formula.py`
- Create: `src/pharmacy_mcp/infrastructure/knowledge/formula_catalog.py`
- Create: `src/pharmacy_mcp/data/formulas/trusted_pk_ddi.json`
- Test: `tests/test_formula_catalog.py`

- [ ] **Step 1: Write failing tests**

Create tests that load the catalog, assert six formula IDs exist, assert each formula has references/assumptions/limitations, and assert unknown formula lookup returns `None`.

- [ ] **Step 2: Run test to verify failure**

Run: `uv run pytest tests/test_formula_catalog.py -v`
Expected: FAIL because the module does not exist yet.

- [ ] **Step 3: Implement formula value objects and catalog**

Implement immutable metadata objects and a loader that reads bundled JSON with UTF-8.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_formula_catalog.py -v`
Expected: PASS.

## Task 2: Simulation Engine

**Files:**
- Create: `src/pharmacy_mcp/application/services/simulation.py`
- Test: `tests/test_simulation.py`

- [ ] **Step 1: Write failing tests**

Test one-compartment concentration, accumulation factor, CYP inhibition AUC ratio, renal clearance adjustment, temperature correction, invalid parameters, and inclusion of disclaimer/limitations.

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/test_simulation.py -v`
Expected: FAIL because simulation service does not exist.

- [ ] **Step 3: Implement simulation service**

Implement deterministic formula methods and structured result dictionaries.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_simulation.py -v`
Expected: PASS.

## Task 3: Interaction Integration

**Files:**
- Modify: `src/pharmacy_mcp/application/services/interaction.py`
- Test: `tests/test_services.py` or new `tests/test_interaction_simulation.py`

- [ ] **Step 1: Write failing tests**

Test that warfarin + fluconazole returns a CYP2C9 mechanism explanation and that simvastatin + strong CYP3A inhibitor can return a simulated exposure ratio.

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/test_interaction_simulation.py -v`
Expected: FAIL because new methods do not exist.

- [ ] **Step 3: Implement interaction service additions**

Add mechanism rules and delegate numeric calculations to `SimulationService`.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_interaction_simulation.py -v`
Expected: PASS.

## Task 4: MCP Tools, Resources, And Prompts

**Files:**
- Modify: `src/pharmacy_mcp/presentation/server.py`
- Modify: `tests/test_server.py`

- [ ] **Step 1: Write failing server tests**

Assert new tools are registered, formula resources are readable, prompts are listed, and a simulation tool call returns structured data.

- [ ] **Step 2: Run focused server tests**

Run: `uv run pytest tests/test_server.py -v`
Expected: FAIL because new MCP surface is missing.

- [ ] **Step 3: Register tools/resources/prompts**

Add FastMCP decorators using existing server style.

- [ ] **Step 4: Run focused server tests**

Run: `uv run pytest tests/test_server.py -v`
Expected: PASS.

## Task 5: Quality Modernization

**Files:**
- Modify: `pyproject.toml`
- Modify typed source files as needed
- Add: `.github/workflows/ci.yml`

- [ ] **Step 1: Run current quality gates**

Run ruff, mypy, bandit, coverage, and build to collect failures.

- [ ] **Step 2: Fix ruff and bandit**

Use `uv run ruff check src tests --fix` for safe fixes and manually replace MD5 cache keys with SHA-256 or `usedforsecurity=False`.

- [ ] **Step 3: Make mypy achievable**

Type new code strictly. For inherited large modules, add narrow overrides only where necessary and document them.

- [ ] **Step 4: Add CI workflow**

Add GitHub Actions with uv setup, Python 3.11/3.12 matrix, tests, ruff, mypy, bandit, and build.

## Task 6: Docs, Harness, And Release Metadata

**Files:**
- Modify: `README.md`
- Modify: `README.zh-TW.md`
- Modify: `CHANGELOG.md`
- Modify: `ROADMAP.md`
- Modify: `src/pharmacy_mcp/__init__.py`
- Modify: `pyproject.toml`
- Include: `.codex`, `.claude`, `.cline`, `.clinerules`, `.github/agents`, `.github/hooks`, `scripts`

- [ ] **Step 1: Update version to 0.9.0**

Set package and module versions to `0.9.0`.

- [ ] **Step 2: Update documentation**

Document actual tool names, simulation disclaimer, formula catalog, external NSForge companion model, and verification commands.

- [ ] **Step 3: Ensure harness assets are tracked**

Keep assistant harness files and workflow docs synchronized. If no `package.json` exists, document that `npm run sync-assets` is not applicable in this repo state.

- [ ] **Step 4: Run final verification**

Run all release gates and fix failures until green or clearly document an external blocker.

## Self-Review

- Spec coverage: Tasks cover formula catalog, simulation, MCP surface, harness, docs, CI, and release metadata.
- Placeholder scan: No deferred implementation placeholders are used for 0.9.0 scope.
- Type consistency: Formula catalog feeds SimulationService, InteractionService, and MCP server tools.
