# Pharmaceutical knowledge source catalog

`list_knowledge_sources` is the runtime source of truth. It reports both the
catalog status and whether an executable adapter is actually registered.

| Provider ID | Source | Coverage | State |
|---|---|---|---|
| `rxnorm` / `rxclass` | [NLM RxNav](https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html) | identity, normalized names, classes | ready |
| `openfda` | [openFDA Drug APIs](https://open.fda.gov/apis/drug/) | labels, adverse events, NDC, recalls, approvals, Orange Book, shortages | ready |
| `dailymed` | [DailyMed SPL v2](https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm) | current structured labels | ready |
| `pubchem` | [PubChem PUG REST](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest) | compound identity and chemistry | ready |
| `medlineplus-connect` | [MedlinePlus Connect](https://medlineplus.gov/medlineplus-connect/web-service/) | patient education by RxCUI/NDC/name | ready |
| `pubmed` | [NCBI PubMed E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25497/) | literature citation discovery | ready |
| `clinical-trials-gov` | [ClinicalTrials.gov API v2](https://clinicaltrials.gov/data-api/api) | intervention studies, phases, status and indications | ready |
| `chembl` | [EMBL-EBI ChEMBL REST](https://www.ebi.ac.uk/chembl/api/data/docs) | molecule identity, chemistry, mechanisms, targets and bioactivity | ready |
| `open-targets` | [Open Targets GraphQL](https://platform-docs.opentargets.org/data-access/graphql-api) | drug targets, mechanisms and indications | ready |
| `tw-tfda` | [TFDA open data](https://data.gov.tw/dataset/9122) | permits, ingredients, product identity | ready |
| `tw-nhi` | [NHI drug-item dataset](https://info.nhi.gov.tw/IODE0000/IODE0000S09?id=111) | reimbursement item and coverage metadata | ready |
| `fhir` | [HL7 FHIR](https://hl7.org/fhir/) | hospital medications, formulary, orders, dispense and inventory | ready; endpoint required |
| `wcf` | configured internal SOAP/WCF service | local medication identity, formulary, stock and status fields | ready; private contract + field allowlists required |
| `local-formulary` | bundled or hospital formulary | local product rules | ready |
| `sql` | allowlisted read-only SQLite | formulary, price, inventory | ready; mapping required |
| `vector` | organization vector gateway | semantic document retrieval | ready; endpoint required |
| `file` | PDF, DOC/DOCX, CSV, XLS/XLSX, Markdown, text | local documents and data extracts | ready; `knowledge/` by default |
| `web` | fixed HTTPS documents | supplemental documents and literature | ready; URL list required |
| `drugbank` | [DrugBank](https://dev.drugbank.com/) | identity, pharmacology, interactions | license required |
| `first-databank` | [FDB](https://www.fdbhealth.com/) | clinical drug knowledge | license required |
| `micromedex` | [Merative Micromedex](https://www.merative.com/clinical-decision-support) | clinical drug knowledge | license required |

`ready` means an adapter ships in this repository; the text after the semicolon
states whether runtime configuration is required. `license_required` is never silently scraped or used
without an organization's credentials and data license.

See [organization knowledge connectors](connectors.md) for file formats,
environment settings, vector request shape, and the SQL/web security boundary.
See [operations and source health](operations.md) for the scheduled live probes.
The [coverage and evidence matrix](coverage-matrix.md) maps each requested
knowledge surface to executable code, tests, and its safety boundary.

## Compound query behavior

`query_pharmacy` selects providers by required capability or by explicit source
IDs, runs them concurrently, and isolates failures. If one source fails while
another succeeds, the response status is `partial`; each failure remains in the
top-level `errors` list and successful provenance remains in `sources`.

The provider registry is deliberately transport-neutral. An API, FHIR server,
SQL database, SOAP/WCF service, vector index, file collection, or allowlisted website implements
the same `KnowledgeProvider.query(ProviderQuery)` port.

## Clinical safety boundary

Public and open datasets are reference material, not a substitute for licensed
clinical decision support or professional judgment. The gateway preserves each
provider's provenance and warnings so agents cannot present merged data as if it
came from one authoritative clinical source.
