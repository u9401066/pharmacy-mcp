# Public pharmaceutical APIs

The gateway ships executable adapters for the following no-license public
interfaces. They all return through the same provider result and top-level MCP
response contracts.

## NLM RxNorm and RxClass

RxNorm normalizes drug names to RxCUIs and RxClass maps those concepts to drug
classes. The adapter covers concept search, concept detail, and class lookup.

Official documentation: <https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html>

## FDA openFDA

The adapter currently projects product-label search into bounded agent results.
The catalog also records openFDA's drug event, NDC, recall, Orange Book,
Drugs@FDA, and shortage endpoint capabilities for subsequent query modes.

Official documentation: <https://open.fda.gov/apis/drug/>

openFDA explicitly warns that public records are not validated for direct
medical-care decisions. Agents must retain the gateway disclaimer.

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
