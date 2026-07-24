# Architecture

## System boundary

Pharmacy MCP is a read-mostly pharmaceutical knowledge gateway with one
versioned agent-facing response. MCP, Python, and CLI are transports over the
same application service; they are not independent implementations.

```text
MCP client             Python agent              shell/job
    │                       │                         │
    └─────────────── PharmacyHarness / tools ────────┘
                            │
                    UnifiedQueryService
                            │
                      ProviderRegistry
          ┌─────────────────┼──────────────────┐
          │                 │                  │
     public/Taiwan      FHIR/hospital      organization data
       APIs/data       meds + inventory   file/SQL/WCF/vector/web
          └─────────────────┼──────────────────┘
                            │
                    QueryResponse v1.0
```

## Layers

- `domain/` defines the provider port, capabilities, response contract, drug
  entities, and value objects. It does not perform I/O.
- `application/` owns use cases. `UnifiedQueryService` normalizes a query,
  chooses providers, enforces fan-out/concurrency budgets and per-provider
  timeouts, and aggregates traceable partial results. `ConnectorAccessService`
  owns safe document retrieval and FHIR capability inspection.
- `infrastructure/` contains API/FHIR clients, the NHI index, local knowledge,
  parsers, and provider adapters. Every executable source implements
  `KnowledgeProvider.query(ProviderQuery)`.
- `presentation/` exposes MCP tools/prompts and the CLI. It validates and
  deterministically renders results; it does not own source-specific logic.

Dependencies point inward. Infrastructure implements domain ports, application
orchestrates those ports, and presentation calls application services.

## Query lifecycle

1. A caller supplies text, required capabilities, optional explicit sources,
   limit, and authorized provider context.
2. `ProviderRegistry` resolves configured adapters. Missing explicit providers
   become `provider_unavailable` errors.
3. The service rejects fan-out above `provider_max_per_query`, then executes at
   most `provider_max_parallel` providers concurrently with isolated timeouts
   and exceptions. These limits are operator policy, not caller arguments.
4. Successful provider payloads remain keyed by provider ID. Provenance is
   deduplicated without merging source authority.
5. The service selects `ok`, `partial`, or `error` and returns `ServiceResult`.
6. The transport wraps it in JSON-Schema-validated `QueryResponse` v1.0 and
   produces the requested text view.

## Source model

The catalog describes every known integration; the registry describes what can
execute now. These states are intentionally separate:

- `ready`: adapter code ships with the repository;
- `license_required`: integration requires organization licensing and remains
  unregistered by default;
- `registered`: the required runtime configuration is present.

Adapters are selected by normalized capabilities such as `identity`, `label`,
`safety`, `reimbursement`, `formulary`, `inventory`, `document`, and
`chemistry`. Callers may specify source IDs for reproducibility.

## Storage and refresh

- Public API responses use bounded projections so large upstream payloads do
  not flood agent context.
- The official Taiwan NHI monthly CSV is streamed into a temporary, versioned
  SQLite database and atomically replaces the active index after validation.
- The bundled formulary and renal-dose data remain small versioned assets.
- Operator databases are opened read-only and expose only validated table and
  column mappings.
- SOAP/WCF contracts and field allowlists remain deployment settings; snapshots
  use secure XML parsing, byte/record limits, and a TTL cache before projection.
- File extraction is bounded by root, extension, symlink, byte, and file-count
  policy. Search emits opaque document IDs, extracted-text SHA-256 revisions,
  and exact line/character spans; bounded reads accept IDs rather than paths.

## Security and privacy

- Credentials come from server settings and never from MCP arguments.
- FHIR is read-only. Patient resources require explicit `context.patient_id`;
  authentication, SMART token rotation, consent, audit, and authorization stay
  with the hospital environment.
- Vector forwarding includes only query, limit, and explicit `vector_filters`.
- Fixed web retrieval accepts only operator-configured, credential-free HTTPS
  URLs, does not follow redirects, and enforces byte limits.
- The gateway does not claim that public/open data is clinical decision support.

See [SECURITY.md](SECURITY.md), [docs/fhir.md](docs/fhir.md), and
[docs/connectors.md](docs/connectors.md).

## Compatibility policy

Adding provider payload fields is normally backward compatible. Changing the
top-level envelope, field meaning, or required fields requires a new
`schema_version`. Human renderers may improve without becoming authoritative.
Existing atomic tools remain available for deterministic legacy workflows while
new cross-source work should prefer `query_pharmacy`.
