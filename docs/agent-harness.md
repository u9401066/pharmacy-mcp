# Agent harness and stable output

Pharmacy MCP provides three views of the same single-entry query workflow:

- MCP tool `query_pharmacy` for MCP-native agents;
- Python `PharmacyHarness` for application and orchestration code;
- `pharmacy-query` for shells, jobs, and harness smoke tests.

All three return a validated `QueryResponse` v1.0. The response has exactly
these top-level fields: `schema_version`, `status`, `data`, `sources`,
`warnings`, `errors`, and `meta`. `structuredContent` is authoritative in MCP;
the text content is only a deterministic JSON, compact JSON, or Markdown view.
See the full [response contract](architecture/response-contract.md).

## MCP agent constraint

Every MCP tool description carries the forwarding rules and the same
`outputSchema`. MCP clients may also request the `pharmacy-query-contract`
prompt with optional `output_format` and `locale` arguments. The prompt tells an
agent to preserve provenance and failures, avoid filling in absent clinical
facts, keep secrets out of tool arguments, and emit JSON without surrounding
prose or code fences.

## Python

```python
import asyncio

from pharmacy_mcp.application.harness import PharmacyHarness


async def main() -> None:
    harness = PharmacyHarness()
    response = await harness.query(
        "warfarin",
        capabilities=["identity", "label", "reimbursement", "formulary"],
        sources=["rxnorm", "dailymed", "tw-tfda", "tw-nhi", "local-formulary"],
        output_format="json_compact",
        locale="zh-TW",
    )
    print(harness.render(response))


asyncio.run(main())
```

Use `response.model_dump(mode="json")` when handing the structured object to
another Python component. Do not parse the human-oriented Markdown rendering.

## Command line

```bash
uv run pharmacy-query warfarin \
  --capability formulary \
  --capability reimbursement \
  --source local-formulary \
  --source tw-nhi \
  --format json_compact \
  --locale zh-TW
```

Repeat `--capability` and `--source` as needed. `--context-json` accepts an
authorized provider context object, for example an explicit FHIR patient scope;
never place access tokens in it. The process exits with status 2 only when the
compound response status is `error`; a traceable `partial` result exits 0.

## Routing expectations

Omitting `--source` lets the registry choose enabled providers matching the
requested capabilities. Explicit sources are preferable in reproducible agent
workflows because they make cost, latency, egress, and provenance predictable.
An unconfigured source yields a machine-actionable `provider_unavailable`
error instead of silently switching to another source.
