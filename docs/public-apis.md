# Public pharmaceutical APIs

The gateway ships executable adapters for the following no-license public
interfaces. They all return through the same provider result and top-level MCP
response contracts.

## NLM RxNorm and RxClass

RxNorm normalizes drug names to RxCUIs and RxClass maps those concepts to drug
classes. `rxnorm` returns identity records; the separate `rxclass` provider
resolves each RxCUI and preserves class ID, class type, relation, and relation
source instead of flattening every membership into an ambiguous name.

Official documentation: <https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html>

## FDA openFDA

The `openfda` provider executes all seven current openFDA drug endpoints. It
routes only the endpoints requested by capability and keeps every payload
bounded before it enters agent context.

| Capability | Result key | Official endpoint |
|---|---|---|
| `label`, `dosing`, `safety`, `interaction` | `labels` | `/drug/label.json` |
| `adverse_event` | `adverse_events` | `/drug/event.json` |
| `ndc` | `ndc` | `/drug/ndc.json` |
| `recall` | `recalls` | `/drug/enforcement.json` |
| `approval` | `approvals` | `/drug/drugsfda.json` |
| `therapeutic_equivalence` | `therapeutic_equivalence` | `/drug/orangebook.json` |
| `shortage` | `shortages` | `/drug/shortages.json` |

`search` intentionally queries labels only. Ask for the explicit capability
when the agent needs surveillance, regulatory, NDC, equivalence, or shortage
records. A failure in one selected endpoint produces `partial` while retaining
the other successful endpoint results.

Official documentation: <https://open.fda.gov/apis/drug/>

openFDA explicitly warns that public records are not validated for direct
medical-care decisions. NDC Directory inclusion does not indicate FDA approval
or reimbursement. Agents must retain the gateway disclaimer and source boundary.

## NLM DailyMed SPL v2

`dailymed` searches current Structured Product Label metadata, including SET ID,
label version, title, publication date, dataset publication date, and paging.
A SET ID can then retrieve a single SPL document through the client API.

Official documentation: <https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm>

## NIH PubChem PUG REST

`pubchem` resolves a compound name to CID, formula, molecular weight, SMILES,
InChI/InChIKey, IUPAC name, XLogP, and polar surface area when available.
PubChem asks clients to remain below five requests per second; normal gateway
timeouts and provider selection prevent bulk crawling through agent calls.

Official documentation: <https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest>

## NLM MedlinePlus Connect

`medlineplus-connect` returns patient-education titles, links, summaries, and
attribution. The client accepts RxCUI or NDC codes and English drug-name fallback;
code-based Spanish queries are also supported by the client.

Official documentation: <https://medlineplus.gov/medlineplus-connect/web-service/>

## Example compound query

```json
{
  "query": "warfarin",
  "sources": ["rxnorm", "openfda", "dailymed", "pubchem", "medlineplus-connect"],
  "limit": 3,
  "output_format": "json"
}
```

A live smoke test on 2026-07-20 returned DailyMed SPL publication metadata,
PubChem CID `54678486`, and MedlinePlus patient education in one `ok` response.
The scheduled source-health workflow also checks RxNorm/RxClass, every openFDA
drug endpoint, both Taiwan download surfaces, and these three sources weekly.
