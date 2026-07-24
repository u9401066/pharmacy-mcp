# System Patterns

Updated: 2026-07-24

## 1. Schema-bound transport edge

`PharmacyFastMCP` decorates every tool with the same `QueryResponse` v1.0
output schema. Tool functions may return domain/application payloads, but the
transport boundary always emits the seven canonical fields. Text renderers are
deterministic views; MCP `structuredContent` is authoritative.

```text
schema_version · status · data · sources · warnings · errors · meta
```

Pattern rule: additive provider details belong under `data`; breaking top-level
changes require a schema version increment.

## 2. Provider port and honest catalog

Heterogeneous sources implement one async `KnowledgeProvider` port using
`ProviderQuery` and `ProviderResult`. The provider catalog describes capability,
license, credentials, and readiness independently from runtime registration.

```python
class KnowledgeProvider(Protocol):
    descriptor: ProviderDescriptor

    async def query(self, request: ProviderQuery) -> ProviderResult: ...
```

Pattern rule: `ready`, `registered`, and `license_required` are distinct states.
Never silently substitute an unavailable provider or claim a licensed source is
enabled.

## 3. Bounded scatter-gather

`UnifiedQueryService` resolves compatible providers, rejects over-budget fan-out
before any I/O, and runs accepted providers behind an `asyncio.Semaphore`.
Per-provider timeout begins after slot acquisition.

```text
resolve → budget check → semaphore slot → provider timeout → typed aggregation
```

Pattern rule: preserve successful payloads and provenance when siblings fail;
return `partial` with typed errors instead of all-or-nothing failure.

## 4. Capability routing

Providers advertise only capabilities they can execute. Expensive discovery
surfaces such as literature, trial, target, indication, and bioactivity require
an explicit capability or source instead of joining every general drug search.

Pattern rule: a catalog claim needs an executable adapter, bounded projection,
provenance, contract tests, and operational health evidence.

## 5. FHIR-native resources inside a stable envelope

The FHIR adapter validates `Bundle.type=searchset` and expected `resourceType`,
but does not flatten unlike FHIR resources into a lossy common record. Raw core
fields, `meta.profile`, `extension`, and organization-defined keys remain intact.

Pattern rule: standardize orchestration and evidence metadata around FHIR; do
not rewrite FHIR resource semantics. Use `CapabilityStatement` inspection to
detect version, resource, interaction, search-parameter, and profile drift.

## 6. Operator-owned connector allowlists

Every organization connector is narrowed at startup:

| Connector | Allowed input | Explicitly rejected |
|---|---|---|
| Files | Query against configured roots | Caller path, symlink, traversal, oversized file |
| SQLite | Query and bound values against configured projection | Caller SQL, write mode, unknown table/column |
| Vector | Query, limit, explicit vector filters | Patient context, caller endpoint |
| Web | Fixed credential-free HTTPS documents | Caller URL, redirect, unsafe destination |
| SOAP/WCF | Fixed URL/action/operation and search fields | Caller contract, unbounded snapshot, unsafe XML |

Pattern rule: an MCP search tool is not a general file, database, or network tool.

## 7. Citation-ready document identity

Search returns a stable opaque ID derived from configured-root index and
root-relative path. Every extraction includes a full-text SHA-256 and exact
half-open character and line spans. Bounded reads resolve only the ID.

Pattern rule: revision hashes identify the extracted text version; locators must
remain exact and reproducible. Never weaken locator integrity to satisfy a test.

## 8. Safe snapshot adapter for legacy SOAP/WCF

The WCF connector treats a no-argument SOAP response as a bounded snapshot:

```text
TLS POST → safe XML parse → JSON object rows → byte/record bounds → TTL cache
                                              ↓
                                   search/output allowlists
```

Pattern rule: MCP performs read-only lookup. Daily materialization, SQLite swap,
spreadsheet generation, or vector rebuild belongs to an external operations
workflow and is not agent-triggerable.

## 9. Atomic local indexes

Large official datasets such as NHI monthly drug items are streamed, validated,
indexed in a temporary SQLite database, then atomically replaced. Schema version
changes trigger rebuilds; queries use the last complete index.

Pattern rule: interrupted refresh must never corrupt the currently usable index.

## 10. Security and resource lifecycle

- Secrets come from environment-backed `SecretStr`, never tool arguments.
- HTTP clients use TLS verification and connector-specific redirect/SSRF rules.
- XML uses `defusedxml`; cache keys use SHA-256.
- SQLite and cache resources have explicit, idempotent close behavior.
- Numeric simulation validates units, ranges, formulas, and finite output.

Pattern rule: fail closed at trust boundaries and degrade only at independent
provider boundaries.

## 11. Verification pattern

Behavior changes require focused regression tests plus the full release gates:
Ruff format/check, strict mypy, branch-coverage tests, Bandit, lock check,
MkDocs strict build, package build, artifact privacy audit, and installed-wheel
MCP smoke.

Pattern rule: mocks prove deterministic contracts; scheduled live probes detect
external source drift. Neither replaces the other.
