# Stable response contract

Every Pharmacy MCP tool exposes the same versioned `outputSchema`. This makes
tool results predictable for small models, deterministic workflows, and typed
agent harnesses.

## Structured content is authoritative

MCP clients should consume `structuredContent`. The text content is only a
rendered view selected with `output_format`:

- `json` — readable, sorted JSON
- `json_compact` — compact, sorted JSON
- `markdown` — human-readable summary containing the complete `data` payload

All renderings originate from the same validated model. Changing the rendering
does not change `structuredContent`.

## Envelope v1.0

```json
{
  "schema_version": "1.0",
  "status": "ok",
  "data": {},
  "sources": [],
  "warnings": [],
  "errors": [],
  "meta": {
    "tool": "search_drug",
    "output_format": "json",
    "locale": "zh-TW",
    "result_count": 0,
    "disclaimer": "..."
  }
}
```

Unknown top-level fields are forbidden. Breaking changes require a new
`schema_version`; additive provider payload changes remain inside `data`.
Execution policy metadata (for example provider count, timeout, fan-out budget,
and concurrency limit) is additive data under `query_pharmacy.data.execution`.
Connector-specific tools that can return partial results use the same
`ServiceResult` to `QueryResponse` conversion as the unified query.

## Agent requirements

Tool descriptions instruct agents to:

1. Treat `structuredContent` as the source of truth.
2. Preserve `schema_version`, `status`, `sources`, `warnings`, `errors`, and
   `meta` when forwarding results.
3. Never invent missing clinical facts.

The MCP SDK validates successful structured results against the declared JSON
Schema before returning them to the client.
