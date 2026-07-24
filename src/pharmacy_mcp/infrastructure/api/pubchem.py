"""NIH PubChem PUG REST compound client."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from pharmacy_mcp.config import settings

PROPERTY_FIELDS = (
    "Title,MolecularFormula,MolecularWeight,CanonicalSMILES,"
    "IsomericSMILES,InChI,InChIKey,IUPACName,XLogP,TPSA"
)


class PubChemClient:
    """Retrieve bounded chemical identity records by drug/compound name."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or settings.pubchem_base_url).rstrip("/") + "/"
        self.timeout = settings.request_timeout
        self.transport = transport

    async def get_compound_by_name(self, name: str) -> dict[str, Any] | None:
        """Return PubChem's normalized identity and calculated properties."""

        encoded_name = quote(name, safe="")
        path = f"compound/name/{encoded_name}/property/{PROPERTY_FIELDS}/JSON"
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            transport=self.transport,
        ) as client:
            response = await client.get(path)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        properties = response.json().get("PropertyTable", {}).get("Properties", [])
        return properties[0] if properties else None
