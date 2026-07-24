# Coverage and verification matrix

The phrase “all drug knowledge APIs” has no finite global registry: public,
licensed, national, research, and hospital sources change independently. This
gateway therefore makes coverage testable by knowledge surface. A source is
called **shipped** only when it has an executable adapter, capability routing,
bounded output, provenance, tests, and an operations path. Licensed products
are cataloged honestly and are never scraped.

## Knowledge surfaces

| Required surface | Executable integration | Capability or route | Verification |
|---|---|---|---|
| Drug name and identifier normalization | RxNorm; ChEMBL; PubChem | `identity`, `chemistry` | mocked API contracts + weekly live probe |
| Classes and mechanisms | RxClass; ChEMBL; Open Targets | `drug_class`, `target` | capability routing + normalized target projections |
| Official product labels and dosing text | DailyMed; openFDA label | `label`, `dosing`, `safety`, `interaction` | current SPL and bounded label contract tests |
| Regulatory and surveillance | openFDA label/event/NDC/enforcement/Drugs@FDA/Orange Book/shortages | explicit endpoint capability | seven independent adapters + seven live probes |
| Patient education | MedlinePlus Connect | `document`, `literature` | normalized entry contract + live probe |
| Literature discovery | PubMed E-utilities | `literature` | ESearch → ESummary contract + live probe |
| Clinical studies | ClinicalTrials.gov API v2 | `clinical_trial`, `indication` | intervention-specific query contract + live probe |
| Targets and experimental bioactivity | ChEMBL REST | `target`, `bioactivity` | molecule/mechanism/activity contracts + live probe |
| Drug–disease evidence | Open Targets GraphQL | `target`, `indication` | schema-checked search/detail contract + live probe |
| Taiwan product and reimbursement | TFDA permits + NHI monthly drug items/rules | `identity`, `label`, `reimbursement` | compound provider, atomic SQLite index, source probes |
| Hospital formulary and inventory | FHIR R4/R5 + local formulary + configured SOAP/WCF | `formulary`, `inventory` | capability/resource validation, patient context, WCF allowlist/cache tests |
| Organization knowledge | files, SQLite, vector gateway, fixed web pages | `document`, `literature`, `formulary`, `inventory` | allowlist/read-only/size and transport tests |
| Deterministic PK/DDI calculation | trusted formula catalog | dedicated MCP simulation tools | fixtures, provenance, numeric fail-closed tests |

## Input and output coverage

The single `query_pharmacy` entry accepts an explicit source list or routes by
capability. Organization adapters cover PDF, DOC/DOCX, CSV, XLS/XLSX, Markdown,
text, read-only SQLite, configured SOAP/WCF, vector HTTP search, and fixed HTTPS pages. FHIR is
registered after an operator sets its endpoint; patient medication resources
require an explicit authorized `context.patient_id`.

Every MCP tool returns `QueryResponse` schema version `1.0` with exactly:

```text
schema_version · status · data · sources · warnings · errors · meta
```

The caller may request deterministic `json`, `json_compact`, or `markdown` text,
while MCP `structuredContent` remains authoritative. Provider failures are
isolated, and successful results remain available with `status=partial`.

## Deliberate boundaries

- DrugBank, First Databank, and Micromedex remain `license_required` catalog
  entries until an organization supplies a lawful licensed adapter.
- Public API data is reference material, not validated clinical decision
  support. The gateway does not synthesize missing clinical facts.
- Generic allowlisted web and vector connectors extend institutional coverage;
  they do not let an agent choose arbitrary URLs, paths, SQL, or credentials.
- New upstreams must add a descriptor, adapter, bounded projection, tests,
  provenance, health check where feasible, and documentation before being
  described as shipped.
