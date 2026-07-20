# Pharmacy MCP Gateway

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/Model_Context_Protocol-server-00695C.svg)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Documentation](https://img.shields.io/badge/docs-GitHub_Pages-00897B.svg)](https://u9401066.github.io/pharmacy-mcp/)

An MCP server and agent harness that makes pharmaceutical knowledge available
through one traceable query contract. It combines public drug APIs, Taiwan
TFDA/NHI data, hospital FHIR and inventory, organization databases, vector
search, files, and fixed web documents.

[繁體中文](README.zh-TW.md) · [Documentation](https://u9401066.github.io/pharmacy-mcp/) · [Architecture](ARCHITECTURE.md)

> Alpha software. Reference data only; not medical advice or a replacement for
> a pharmacist, physician, or validated clinical decision-support system.

## Why this gateway

- **One agent entry point:** `query_pharmacy` routes by capability or explicit
  source and isolates provider timeouts and failures.
- **Stable output:** every MCP tool returns `QueryResponse` v1.0 through a
  shared JSON Schema. Text is a deterministic `json`, `json_compact`, or
  `markdown` rendering; MCP `structuredContent` remains authoritative.
- **Agent constraint:** every tool carries forwarding rules and clients can load
  the `pharmacy-query-contract` MCP prompt.
- **Traceable compound results:** provider payloads, provenance, warnings, and
  errors remain distinct. Successful data survives as `partial` if another
  source fails.
- **Hospital-ready boundaries:** FHIR is read-only; file, SQL, vector, and web
  connectors are configured by operators instead of accepting arbitrary agent
  paths, SQL, endpoints, or URLs.
- **Drift detection:** a scheduled health workflow probes 14 official API and
  dataset surfaces every week without downloading the large Taiwan datasets.

## Quick start

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/u9401066/pharmacy-mcp.git
cd pharmacy-mcp
uv sync --all-extras
uv run pharmacy-mcp
```

MCP client configuration:

```json
{
  "mcpServers": {
    "pharmacy": {
      "command": "uv",
      "args": ["run", "pharmacy-mcp"],
      "cwd": "/absolute/path/to/pharmacy-mcp"
    }
  }
}
```

Recommended tool call:

```json
{
  "query": "warfarin",
  "capabilities": ["identity", "label", "reimbursement", "formulary"],
  "sources": ["rxnorm", "dailymed", "tw-tfda", "tw-nhi", "local-formulary"],
  "limit": 10,
  "output_format": "json_compact",
  "locale": "zh-TW"
}
```

For a shell or non-MCP workflow:

```bash
uv run pharmacy-query warfarin \
  --source local-formulary \
  --capability formulary \
  --format json_compact
```

The Python API exposes the same contract through
`pharmacy_mcp.application.harness.PharmacyHarness`.

## Integrated knowledge

| Area | Shipped adapters |
|---|---|
| Public drug knowledge | RxNorm/RxClass; all seven openFDA drug endpoints; DailyMed; PubChem; MedlinePlus Connect |
| Taiwan | TFDA permits, official NHI monthly drug items, coverage rules and terminology |
| Hospital | FHIR R4/R5 medication, order, dispense, inventory and supply; bundled formulary |
| Organization data | PDF, DOC/DOCX, CSV, XLS/XLSX, Markdown, text, read-only SQLite, vector gateway, fixed HTTPS pages |
| Licensed catalog | DrugBank, FDB and Micromedex are discoverable but never scraped or presented as enabled without a license |

Call `list_knowledge_sources` for the runtime source of truth: capabilities,
implementation state, credential needs, and whether an adapter is registered.
See the [complete data-source catalog](docs/data-sources.md).

## Taiwan NHI and hospital setup

The NHI provider downloads the official monthly CSV on demand and atomically
builds a versioned SQLite index. It can combine reimbursement code, price, ATC,
effective dates, TFDA results, and coverage-rule metadata in one query. See
[Taiwan NHI compound queries](docs/taiwan-nhi.md).

Set `PHARMACY_MCP_FHIR_BASE_URL` to register the hospital adapter. Bearer tokens
are read from `SecretStr` settings, and patient resources are queried only when
an authorized caller explicitly supplies `context.patient_id`. Organization
connectors use similarly explicit allowlists. Start with [.env.example](.env.example),
[FHIR and inventory](docs/fhir.md), and [organization connectors](docs/connectors.md).

## Output and agent rules

The canonical top-level fields are:

```text
schema_version · status · data · sources · warnings · errors · meta
```

Unknown top-level fields are rejected. Agents must preserve all seven fields,
must not infer absent clinical facts, and must not flatten multiple providers
into one implied authority. See the [agent harness guide](docs/agent-harness.md)
and [response contract](docs/architecture/response-contract.md).

## Development

```bash
uv sync --all-extras
uv run pytest
uv run ruff check src tests examples scripts
uv run mypy src
uv run mkdocs build --strict
uv run python scripts/check_source_health.py
```

The repository uses segmented Conventional Commits, an updated Memory Bank, CI
across supported Python versions, weekly public-source health checks, and a
GitHub Pages documentation workflow.
See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## License

Apache License 2.0. Upstream datasets and commercial knowledge bases retain
their own terms, attribution requirements, and clinical-use restrictions.
