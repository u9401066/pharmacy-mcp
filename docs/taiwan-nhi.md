# Taiwan NHI compound queries

Pharmacy MCP uses the National Health Insurance Administration's official
monthly **健保用藥品項查詢項目檔** rather than the retired `data.nhi.gov.tw` URL.

- Dataset page: <https://info.nhi.gov.tw/IODE0000/IODE0000S09?id=111>
- OAS resource ID: `A21030000I-E41001-001`
- Current CSV endpoint: `https://info.nhi.gov.tw/api/iode0000s01/Dataset?rId=A21030000I-E41001-001`
- Published encoding: UTF-8 CSV
- Refresh policy: local index is considered fresh for 7 days

The upstream CSV is currently about 97 MB and contains historical price rows.
The first NHI item query streams it to a temporary file, validates headers,
builds a new SQLite database, and atomically replaces the previous index. No
partial database is exposed to queries.

## Compound result

The Taiwan provider merges, without flattening provenance:

1. TFDA permit/product matches.
2. NHI current item rows and payment prices.
3. NHI coverage-rule metadata, including prior authorization when known.
4. Chinese/English normalization from the local fallback map.

Historical NHI rows remain in the index, but normal agent queries return only
currently effective rows. ROC dates are compared numerically so six-digit dates
from years before ROC 100 are not mistaken for future dates.

## Configuration

```dotenv
PHARMACY_MCP_NHI_INDEX_PATH=.cache/nhi/drug-items.sqlite3
PHARMACY_MCP_NHI_AUTO_DOWNLOAD=true
PHARMACY_MCP_NHI_REFRESH_DAYS=7
PHARMACY_MCP_NHI_DOWNLOAD_TIMEOUT_SECONDS=300
```

Set `PHARMACY_MCP_NHI_AUTO_DOWNLOAD=false` in offline or tightly controlled
environments. Existing indexes remain queryable. Use the
`get_nhi_data_status` MCP tool to inspect readiness and provenance without
triggering a download.

## Operational note

Payment prices and coverage rules change. Every result includes effective dates
and source links; agents must not present cached values as current without
checking index freshness and the official NHI publication.
