"""Contract tests for public pharmaceutical knowledge API adapters."""

from typing import Any

import httpx
import pytest

from pharmacy_mcp.infrastructure.api.dailymed import DailyMedClient
from pharmacy_mcp.infrastructure.api.medlineplus import (
    NDC_OID,
    MedlinePlusClient,
)
from pharmacy_mcp.infrastructure.api.pubchem import PubChemClient
from pharmacy_mcp.infrastructure.providers.registry import build_default_registry


@pytest.mark.asyncio
async def test_dailymed_search_normalizes_data_and_metadata() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["drug_name"] == "warfarin"
        assert request.url.params["pagesize"] == "2"
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "setid": "set-1",
                        "title": "WARFARIN TABLET",
                        "spl_version": 3,
                    }
                ],
                "metadata": {"total_elements": 1},
            },
        )

    client = DailyMedClient(transport=httpx.MockTransport(handler))

    result = await client.search_spls("warfarin", 2)

    assert result["results"][0]["setid"] == "set-1"
    assert result["metadata"]["total_elements"] == 1


@pytest.mark.asyncio
async def test_pubchem_returns_first_compound_property_record() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert "/compound/name/warfarin/property/" in request.url.path
        return httpx.Response(
            200,
            json={
                "PropertyTable": {
                    "Properties": [
                        {
                            "CID": 54678486,
                            "Title": "Warfarin",
                            "MolecularFormula": "C19H16O4",
                        }
                    ]
                }
            },
        )

    client = PubChemClient(transport=httpx.MockTransport(handler))

    result = await client.get_compound_by_name("warfarin")

    assert result is not None
    assert result["CID"] == 54678486


@pytest.mark.asyncio
async def test_medlineplus_normalizes_patient_education_entries() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["mainSearchCriteria.v.cs"] == NDC_OID
        assert request.url.params["mainSearchCriteria.v.dn"] == "warfarin"
        return httpx.Response(
            200,
            json={
                "feed": {
                    "entry": [
                        {
                            "title": {"_value": "Warfarin"},
                            "link": [
                                {
                                    "rel": "alternate",
                                    "href": "https://medlineplus.gov/warfarin.html",
                                }
                            ],
                            "summary": {"_value": "Patient information"},
                            "updated": {"_value": "2026-07-20T00:00:00Z"},
                        }
                    ]
                }
            },
        )

    client = MedlinePlusClient(transport=httpx.MockTransport(handler))

    result = await client.search_medication(drug_name="warfarin")

    assert result == [
        {
            "title": "Warfarin",
            "url": "https://medlineplus.gov/warfarin.html",
            "summary_html": "Patient information",
            "updated": "2026-07-20T00:00:00Z",
            "source": "MedlinePlus.gov",
        }
    ]


def test_public_api_adapters_are_registered_and_truthfully_ready() -> None:
    catalog = build_default_registry().catalog()
    by_id: dict[str, dict[str, Any]] = {item["id"]: item for item in catalog}

    for provider_id in ("dailymed", "pubchem", "medlineplus-connect"):
        assert by_id[provider_id]["state"] == "ready"
        assert by_id[provider_id]["registered"] is True
