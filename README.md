# Pharmacy MCP Server

Pharmacy MCP is a Python MCP server for medication reference workflows. It
combines drug search, label summaries, dosing calculators, Taiwan TFDA/NHI
lookups, hospital prescription helpers, and a trusted PBPK-lite formula catalog
for educational PK/DDI simulation.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-1.27+-green.svg)](https://modelcontextprotocol.io/)

Traditional Chinese: [README.zh-TW.md](README.zh-TW.md)

## What Is New In 0.9.1

- Hardened interaction outputs so local database guidance is surfaced as
  non-prescriptive management considerations with safety metadata.
- Added fail-closed simulation guardrails for NaN, infinity, unstable
  denominators, and catalog metadata drift.
- Added release artifact auditing and packaged-wheel smoke tests.
- Made Streamable HTTP ASGI exports lazy and mount-aware.

## What Is New In 0.9.0

- Built-in trusted PK/DDI formula catalog under `src/pharmacy_mcp/data/formulas/`.
- Deterministic simulation service for one-compartment concentration, repeated-dose accumulation, renal clearance adjustment, CYP reversible inhibition, AUC ratio, and temperature-corrected elimination.
- Mechanism-aware DDI tools for supported CYP inhibition examples such as warfarin/fluconazole and statin/clarithromycin.
- Modern MCP surfaces: tools, read-only resources, resource templates, prompts, Streamable HTTP deployment helpers, and structured outputs.
- Release gates for pytest coverage, ruff, mypy, bandit, package build, and
  artifact audit.

Simulation outputs are screening estimates only. They always include the project
disclaimer and `not_for_direct_clinical_decision: true`.

## Install

```bash
git clone https://github.com/u9401066/pharmacy-mcp.git
cd pharmacy-mcp
uv sync --all-extras
```

## Run

```bash
# stdio transport for local MCP clients
uv run pharmacy-mcp

# explicit stdio
uv run pharmacy-mcp --transport stdio

# Streamable HTTP
uv run pharmacy-mcp --transport streamable-http --host 0.0.0.0 --port 8000

# ASGI app
uv run uvicorn pharmacy_mcp.presentation.server:app --host 0.0.0.0 --port 8000
```

Environment variables use the `PHARMACY_MCP_` prefix. Supported settings include
`PHARMACY_MCP_TRANSPORT`, `PHARMACY_MCP_HOST`, `PHARMACY_MCP_PORT`,
`PHARMACY_MCP_MOUNT_PATH`, `PHARMACY_MCP_STREAMABLE_HTTP_PATH`, and
`PHARMACY_MCP_STATELESS_HTTP`.

## Claude Desktop Example

```json
{
  "mcpServers": {
    "pharmacy": {
      "command": "uv",
      "args": ["run", "pharmacy-mcp", "--transport", "stdio"],
      "cwd": "/path/to/pharmacy-mcp"
    }
  }
}
```

## MCP Tools

Drug reference:

- `search_drug`
- `get_drug_info`
- `get_drug_dosage`
- `get_drug_warnings`
- `check_drug_interaction`
- `check_multi_drug_interactions`
- `check_food_drug_interaction`

Dosing calculators:

- `calculate_dose_by_weight`
- `calculate_dose_by_bsa`
- `calculate_creatinine_clearance`
- `calculate_pediatric_dose`
- `calculate_infusion_rate`
- `convert_dose_units`

Taiwan TFDA/NHI:

- `search_tfda_drug`
- `get_nhi_coverage`
- `get_nhi_drug_price`
- `translate_drug_name`
- `list_prior_authorization_drugs`
- `list_nhi_coverage_rules`

Hospital prescription workflow:

- `get_formulary_item`
- `search_formulary`
- `get_renal_adjustment`
- `validate_order`
- `submit_order`
- `stop_order`

Trusted formula and simulation:

- `list_formula_catalog`
- `get_formula_details`
- `explain_interaction_mechanism`
- `simulate_pk_interaction`
- `simulate_concentration_time`

## MCP Resources And Prompts

Resources:

- `pharmacy://server/disclaimer`
- `pharmacy://formulas`
- `pharmacy://formulas/{formula_id}`
- `pharmacy://validation/formulas`

Prompts:

- `ddi_analysis_workflow`
- `formula_review_checklist`

## Trusted Formula Model

Formula metadata is committed as data, not executed as arbitrary runtime code.
Each trusted formula has an ID, expression, parameters, units, assumptions,
limitations, references, and validation cases. The Python simulation service
dispatches by formula ID to reviewed implementations.

External formula generators such as NSForge can be used as companion authoring
tools, but Pharmacy MCP does not vendor NSForge in 0.9.x. Generated formulas
must be reviewed, committed to the trusted catalog, and covered by tests before
production tools can use them.

## Data Sources

| Source | Provider | Data |
| --- | --- | --- |
| RxNorm API | NIH/NLM | Drug names and concepts |
| openFDA | FDA | Drug labels and warnings |
| DailyMed | NLM | Label sections |
| TFDA Open Data | Taiwan TFDA | Taiwan permits and drug names |
| NHI Open Data | Taiwan NHI | Coverage rules and reimbursement data |
| Local catalog | Pharmacy MCP | Trusted PK/DDI formulas and hospital mock data |

## Architecture

```text
src/pharmacy_mcp/
  domain/                  Entities and value objects
  application/services/    Use-case services and simulation orchestration
  infrastructure/api/      External API clients
  infrastructure/cache/    Disk cache adapter
  infrastructure/knowledge/Local formularies and trusted formula catalog
  presentation/            FastMCP server, tools, resources, prompts
```

## Verification

```bash
uv run pytest --cov=src --cov-report=term-missing
uv run ruff check src tests
uv run mypy src
uv run bandit -q -r src
uv build
uv run python scripts/audit_release_artifacts.py dist
```

## Disclaimer

This project is for reference, education, and workflow support only. It does not
provide medical advice and must not be used as the sole basis for clinical
decisions. Consult qualified healthcare professionals and validated clinical
systems for patient care.

## License

[Apache License 2.0](LICENSE)
