# Pharmaceutical knowledge source catalog

`list_knowledge_sources` is the runtime source of truth. It reports both the
catalog status and whether an executable adapter is actually registered.

| Provider ID | Source | Coverage | State |
|---|---|---|---|
| `rxnorm` / `rxclass` | [NLM RxNav](https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html) | identity, normalized names, classes | ready |
| `openfda` | [openFDA Drug APIs](https://open.fda.gov/apis/drug/) | labels, adverse events, NDC, recalls, approvals, shortages | ready |
| `dailymed` | [DailyMed SPL v2](https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm) | current structured labels | ready |
| `pubchem` | [PubChem PUG REST](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest) | compound identity and chemistry | ready |
| `medlineplus-connect` | [MedlinePlus Connect](https://medlineplus.gov/medlineplus-connect/web-service/) | patient education by RxCUI/NDC/name | ready |
| `tw-tfda` | [TFDA open data](https://data.gov.tw/dataset/9122) | permits, ingredients, product identity | ready |
| `tw-nhi` | [NHI drug-item dataset](https://info.nhi.gov.tw/IODE0000/IODE0000S09?id=111) | reimbursement item and coverage metadata | ready |
| `fhir` | [HL7 FHIR](https://hl7.org/fhir/) | hospital medications, formulary, orders, dispense and inventory | ready; endpoint required |
| `local-formulary` | bundled or hospital formulary | local product rules | ready |
| `sql` | operator-defined SQL | formulary, price, inventory | configurable |
| `vector` | operator-defined vector DB | semantic document retrieval | configurable |
| `file` | PDF, DOCX, CSV, XLSX, Markdown | local documents and data extracts | configurable |
| `web` | allowlisted HTTPS sites | supplemental documents and literature | configurable |
| `drugbank` | [DrugBank](https://dev.drugbank.com/) | identity, pharmacology, interactions | license required |
| `first-databank` | [FDB](https://www.fdbhealth.com/) | clinical drug knowledge | license required |
| `micromedex` | [Merative Micromedex](https://www.merative.com/clinical-decision-support) | clinical drug knowledge | license required |

`ready` means an adapter ships in this repository. `configurable` means the
provider contract and routing ID are reserved, but an endpoint, index, or local
path must be configured. `license_required` is never silently scraped or used
without an organization's credentials and data license.

## Compound query behavior

`query_pharmacy` selects providers by required capability or by explicit source
IDs, runs them concurrently, and isolates failures. If one source fails while
another succeeds, the response status is `partial`; each failure remains in the
top-level `errors` list and successful provenance remains in `sources`.

The provider registry is deliberately transport-neutral. An API, FHIR server,
SQL database, vector index, file collection, or allowlisted website implements
the same `KnowledgeProvider.query(ProviderQuery)` port.

## Clinical safety boundary

Public and open datasets are reference material, not a substitute for licensed
clinical decision support or professional judgment. The gateway preserves each
provider's provenance and warnings so agents cannot present merged data as if it
came from one authoritative clinical source.
