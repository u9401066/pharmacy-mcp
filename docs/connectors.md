# Organization knowledge connectors

The unified `query_pharmacy` tool can search organization-owned files, a
read-only SQLite database, an internal vector-search gateway, and a fixed set
of HTTPS pages. These connectors share the normal `QueryResponse` envelope and
retain their own provenance. They are deliberately configured by an operator;
an agent cannot provide a path, SQL statement, vector endpoint, or URL.

## Local files

`PHARMACY_MCP_FILE_ROOTS` is a comma-separated list of administrator-controlled
directories. It defaults to the repository's `knowledge/` directory.

Supported formats are PDF, DOC/DOCX, CSV, XLS/XLSX, Markdown, and plain text.
Modern formats are parsed in-process. Legacy `.doc` extraction requires the
optional `antiword` executable. Symlinks, paths outside an allowed root,
unsupported extensions, over-sized files, and scans beyond the configured
file count are rejected or reported as warnings.

```dotenv
PHARMACY_MCP_FILE_ROOTS=/srv/pharmacy/policies,/srv/pharmacy/formulary
PHARMACY_MCP_FILE_MAX_BYTES=20971520
PHARMACY_MCP_FILE_MAX_FILES=500
```

## Read-only SQLite

The SQL connector does not accept SQL from an MCP caller. The operator provides
a database path and a JSON allowlist of tables, searchable columns, and returned
columns. Identifiers are validated and values remain bound parameters. The
database is opened with SQLite `mode=ro`.

```dotenv
PHARMACY_MCP_SQL_DATABASE_PATH=/srv/pharmacy/formulary.sqlite3
PHARMACY_MCP_SQL_TABLES=[{"table":"medications","search_columns":["code","name","ingredient"],"output_columns":["code","name","ingredient","stock"]}]
```

Use a database view when row-level or column-level access needs to be narrower
than the underlying table. Never add secrets or unrestricted patient tables to
the output projection.

## Vector-search gateway

`PHARMACY_MCP_VECTOR_SEARCH_URL` points to an organization-managed HTTPS search
gateway. The connector posts the following vendor-neutral JSON contract:

```json
{
  "query": "warfarin interaction",
  "limit": 10,
  "filters": {"department": "pharmacy"}
}
```

The response may be a result array or `{ "results": [...] }`. Only the explicit
`context.vector_filters` object is forwarded; patient context and other MCP
arguments are not sent. An optional bearer key is read from a secret setting and
is never placed in tool arguments or results.

```dotenv
PHARMACY_MCP_VECTOR_SEARCH_URL=https://vector.internal.example/search
PHARMACY_MCP_VECTOR_API_KEY=replace-with-short-lived-service-token
PHARMACY_MCP_VECTOR_VERIFY_TLS=true
```

## Fixed HTTPS pages

`PHARMACY_MCP_WEB_URLS` is a JSON array of credential-free HTTPS documents. The
server does not follow redirects and enforces a response-size limit. URLs are
chosen at startup by the operator; an agent cannot turn this connector into a
general web browser or an SSRF primitive.

```dotenv
PHARMACY_MCP_WEB_URLS=["https://hospital.example/pharmacy/bulletins.html"]
PHARMACY_MCP_WEB_MAX_BYTES=2097152
```

For authenticated or dynamic sites, place an approved internal retrieval
service in front of the content and expose it through the vector gateway or a
purpose-built provider instead of embedding credentials in a URL.

## Runtime discovery

Call `list_knowledge_sources` to distinguish shipped support (`state: ready`)
from runtime availability (`registered: true`). The file connector is normally
registered because `knowledge/` is the default root. SQL, vector, and web are
registered only after their required settings are present.
