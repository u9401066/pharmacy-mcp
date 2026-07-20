# Hospital FHIR and inventory

The `fhir` provider is shipped but registers only when
`PHARMACY_MCP_FHIR_BASE_URL` is set. This keeps an unconfigured deployment
honest: `list_knowledge_sources` reports `state=ready` and `registered=false`.

## Configuration

```dotenv
PHARMACY_MCP_FHIR_BASE_URL=https://hospital.example/fhir
PHARMACY_MCP_FHIR_BEARER_TOKEN=short-lived-access-token
PHARMACY_MCP_FHIR_VERSION=R4
PHARMACY_MCP_FHIR_VERIFY_TLS=true
PHARMACY_MCP_FHIR_MEDICATION_RESOURCES=MedicationKnowledge,Medication
PHARMACY_MCP_FHIR_INVENTORY_RESOURCES=InventoryItem,InventoryReport,SupplyDelivery
```

Copy `.env.example` to `.env` for local development. Never commit `.env`.

The bearer token is read as a Pydantic `SecretStr`, placed only in the HTTP
`Authorization` header, and never accepted through MCP arguments or returned in
results. Production SMART Backend Services deployments should obtain and rotate
short-lived tokens through the hospital's token broker. The official SMART flow
uses discovery plus private-key JWT client authentication; static long-lived
tokens are not recommended.

## Resource strategy

| Purpose | R4 | R5 |
|---|---|---|
| Drug/formulary knowledge | `MedicationKnowledge`, `Medication` | same |
| Patient orders | `MedicationRequest` | same |
| Dispensing | `MedicationDispense` | same |
| Inventory product | hospital profile / supply resources | `InventoryItem` |
| Inventory event/report | `SupplyDelivery`, `SupplyRequest` | `InventoryReport`, supply resources |

`InventoryItem` and `InventoryReport` are R5 resources. The default list also
queries `SupplyDelivery`, providing an R4-compatible fallback. Unsupported
resource/search combinations produce provider warnings and do not erase results
from supported resources.

Hospitals that represent inventory through `Basic` or custom profiles may set
the resource list to an allowlisted type and adapt server-side search profiles.
Only known read-only resource types are accepted by the client.

## Unified query

```json
{
  "query": "warfarin",
  "sources": ["fhir"],
  "capabilities": ["formulary", "inventory"],
  "limit": 10
}
```

Patient medication resources are not queried unless an explicit patient ID is
present:

```json
{
  "query": "current medications",
  "sources": ["fhir"],
  "capabilities": ["formulary"],
  "context": {"patient_id": "hospital-patient-id"}
}
```

FHIR search parameters can contain PHI and must be protected as strongly as the
returned resources. Do not enable verbose HTTP access logs in production, use
TLS 1.2+, and grant only the SMART `system/*.rs` or patient/user scopes required
for the selected resources.

Official references:

- <https://hl7.org/fhir/http.html>
- <https://hl7.org/fhir/R4/medicationrequest.html>
- <https://fhir.hl7.org/fhir/inventoryitem.html>
- <https://fhir.hl7.org/fhir/inventoryreport.html>
- <https://hl7.org/fhir/smart-app-launch/STU2.2/backend-services.html>
