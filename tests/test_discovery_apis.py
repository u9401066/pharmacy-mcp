"""Contract tests for literature, trial, target, and bioactivity APIs."""

import json
from typing import Any

import httpx
import pytest

from pharmacy_mcp.domain.models.provider import ProviderQuery, QueryCapability
from pharmacy_mcp.domain.models.response import ResponseStatus
from pharmacy_mcp.infrastructure.api.chembl import ChEMBLClient
from pharmacy_mcp.infrastructure.api.clinical_trials import ClinicalTrialsClient
from pharmacy_mcp.infrastructure.api.open_targets import OpenTargetsClient
from pharmacy_mcp.infrastructure.api.pubmed import PubMedClient
from pharmacy_mcp.infrastructure.providers.builtin import ChEMBLKnowledgeProvider
from pharmacy_mcp.infrastructure.providers.registry import build_default_registry


@pytest.mark.asyncio
async def test_pubmed_runs_search_then_summary_and_projects_citation() -> None:
    calls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        assert request.url.params["db"] == "pubmed"
        assert request.url.params["tool"] == "pharmacy_mcp"
        assert request.url.params["email"] == "owner@example.org"
        assert request.url.params["api_key"] == "secret"
        if request.url.path.endswith("/esearch.fcgi"):
            assert request.url.params["term"] == "warfarin bleeding"
            return httpx.Response(
                200,
                json={"esearchresult": {"idlist": ["123", "not-an-id"]}},
            )
        assert request.url.params["id"] == "123"
        return httpx.Response(
            200,
            json={
                "result": {
                    "123": {
                        "title": "Warfarin safety",
                        "fulljournalname": "Clinical Journal",
                        "pubdate": "2026",
                        "pubtype": ["Journal Article"],
                        "authors": [{"name": "Lin A"}],
                        "articleids": [{"idtype": "doi", "value": "10.1/x"}],
                    }
                }
            },
        )

    client = PubMedClient(
        api_key="secret",
        email="owner@example.org",
        transport=httpx.MockTransport(handler),
    )

    result = await client.search_articles("warfarin bleeding", 2)

    assert calls[0].endswith("/esearch.fcgi")
    assert calls[1].endswith("/esummary.fcgi")
    assert result == [
        {
            "pmid": "123",
            "title": "Warfarin safety",
            "journal": "Clinical Journal",
            "publication_date": "2026",
            "publication_types": ["Journal Article"],
            "authors": ["Lin A"],
            "doi": "10.1/x",
            "url": "https://pubmed.ncbi.nlm.nih.gov/123/",
        }
    ]


@pytest.mark.asyncio
async def test_pubmed_stops_when_search_has_no_valid_identifiers() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"esearchresult": {"idlist": []}})

    result = await PubMedClient(transport=httpx.MockTransport(handler)).search_articles(
        "unknown"
    )

    assert result == []


@pytest.mark.asyncio
async def test_clinical_trials_projects_intervention_study() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["query.intr"] == "warfarin"
        assert request.url.params["pageSize"] == "1"
        return httpx.Response(
            200,
            json={
                "nextPageToken": "next",
                "studies": [
                    {
                        "hasResults": True,
                        "protocolSection": {
                            "identificationModule": {
                                "nctId": "NCT00000001",
                                "briefTitle": "Warfarin study",
                                "officialTitle": "A study of warfarin",
                            },
                            "statusModule": {
                                "overallStatus": "COMPLETED",
                                "startDateStruct": {"date": "2020-01"},
                                "completionDateStruct": {"date": "2025-01"},
                            },
                            "conditionsModule": {"conditions": ["Thrombosis"]},
                            "designModule": {
                                "studyType": "INTERVENTIONAL",
                                "phases": ["PHASE3"],
                            },
                            "armsInterventionsModule": {
                                "interventions": [
                                    {
                                        "type": "DRUG",
                                        "name": "Warfarin",
                                        "description": "x" * 501,
                                    }
                                ]
                            },
                            "sponsorCollaboratorsModule": {
                                "leadSponsor": {"name": "Example sponsor"}
                            },
                        },
                    }
                ],
            },
        )

    result = await ClinicalTrialsClient(
        transport=httpx.MockTransport(handler)
    ).search_studies("warfarin", 1)

    study = result["results"][0]
    assert result["next_page_available"] is True
    assert study["nct_id"] == "NCT00000001"
    assert study["phases"] == ["PHASE3"]
    assert study["interventions"][0]["description"].endswith("…")
    assert study["url"] == "https://clinicaltrials.gov/study/NCT00000001"


@pytest.mark.asyncio
async def test_chembl_projects_molecules_mechanisms_and_activities() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/molecule/search.json"):
            assert request.url.params["q"] == "warfarin"
            return httpx.Response(
                200,
                json={
                    "molecules": [
                        {
                            "molecule_chembl_id": "CHEMBL1464",
                            "pref_name": "WARFARIN",
                            "molecule_type": "Small molecule",
                            "max_phase": 4,
                            "molecule_properties": {
                                "full_molformula": "C19H16O4",
                                "full_mwt": "308.33",
                            },
                            "molecule_structures": {
                                "canonical_smiles": "CC(C1=CC=CC=C1)C(O)=O"
                            },
                            "molecule_synonyms": [{"molecule_synonym": "Coumadin"}],
                        }
                    ]
                },
            )
        if request.url.path.endswith("/mechanism.json"):
            return httpx.Response(
                200,
                json={
                    "mechanisms": [
                        {
                            "molecule_chembl_id": "CHEMBL1464",
                            "mechanism_of_action": "Vitamin K antagonist",
                            "action_type": "INHIBITOR",
                            "target_chembl_id": "CHEMBL2364701",
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "activities": [
                    {
                        "activity_id": 1,
                        "molecule_chembl_id": "CHEMBL1464",
                        "target_chembl_id": "CHEMBL2364701",
                        "standard_type": "IC50",
                        "standard_value": "12.3",
                        "standard_units": "nM",
                    }
                ]
            },
        )

    client = ChEMBLClient(transport=httpx.MockTransport(handler))

    molecules = await client.search_molecules("warfarin", 1)
    mechanisms = await client.get_mechanisms("CHEMBL1464", 1)
    activities = await client.get_activities("CHEMBL1464", 1)

    assert molecules[0]["chembl_id"] == "CHEMBL1464"
    assert molecules[0]["synonyms"] == ["Coumadin"]
    assert mechanisms[0]["mechanism_of_action"] == "Vitamin K antagonist"
    assert activities[0]["standard_units"] == "nM"


@pytest.mark.asyncio
async def test_open_targets_searches_and_fetches_bounded_drug_detail() -> None:
    calls: list[dict[str, Any]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        payload: dict[str, Any] = json.loads(request.content)
        calls.append(payload)
        if "SearchDrugs" in payload["query"]:
            assert payload["variables"]["page"] == {"index": 0, "size": 2}
            return httpx.Response(
                200,
                json={
                    "data": {
                        "search": {
                            "total": 1,
                            "hits": [
                                {
                                    "id": "CHEMBL1464",
                                    "name": "warfarin",
                                    "description": "anticoagulant",
                                    "entity": "drug",
                                }
                            ],
                        }
                    }
                },
            )
        assert payload["variables"] == {"chemblId": "CHEMBL1464"}
        return httpx.Response(
            200,
            json={
                "data": {
                    "drug": {
                        "id": "CHEMBL1464",
                        "name": "WARFARIN",
                        "description": "anticoagulant",
                        "drugType": "Small molecule",
                        "maximumClinicalStage": 4,
                        "synonyms": [{"label": "Warfarin", "source": "ChEMBL"}],
                        "tradeNames": [{"label": "Coumadin", "source": "FDA"}],
                        "mechanismsOfAction": {
                            "rows": [
                                {
                                    "actionType": "INHIBITOR",
                                    "mechanismOfAction": "Vitamin K antagonist",
                                    "targets": [
                                        {
                                            "id": "ENSG1",
                                            "approvedSymbol": "VKORC1",
                                            "approvedName": "VKOR complex subunit 1",
                                        }
                                    ],
                                }
                            ]
                        },
                        "indications": {
                            "count": 1,
                            "rows": [
                                {
                                    "disease": {"id": "EFO1", "name": "Thrombosis"},
                                    "maxClinicalStage": 4,
                                }
                            ],
                        },
                    }
                }
            },
        )

    result = await OpenTargetsClient(
        transport=httpx.MockTransport(handler)
    ).search_drugs("warfarin", 2)

    assert len(calls) == 2
    assert result["total"] == 1
    assert result["details"][0]["trade_names"][0]["label"] == "Coumadin"
    assert (
        result["details"][0]["mechanisms_of_action"][0]["targets"][0]["approved_symbol"]
        == "VKORC1"
    )
    assert result["details"][0]["indications"][0]["disease_name"] == "Thrombosis"


@pytest.mark.asyncio
async def test_open_targets_surfaces_graphql_errors() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"errors": [{"message": "bad query"}]})

    with pytest.raises(RuntimeError, match="Open Targets GraphQL error"):
        await OpenTargetsClient(transport=httpx.MockTransport(handler)).search_drugs(
            "warfarin"
        )


def test_discovery_providers_are_registered_and_capability_routed() -> None:
    registry = build_default_registry()
    catalog = {item["id"]: item for item in registry.catalog()}

    expected = {
        "pubmed": "literature",
        "clinical-trials-gov": "clinical_trial",
        "chembl": "bioactivity",
        "open-targets": "target",
    }
    for provider_id, capability in expected.items():
        assert catalog[provider_id]["registered"] is True
        assert catalog[provider_id]["state"] == "ready"
        assert capability in catalog[provider_id]["capabilities"]

    search_providers, _ = registry.resolve(
        source_ids=None,
        capabilities=(QueryCapability.SEARCH,),
    )
    literature_providers, _ = registry.resolve(
        source_ids=None,
        capabilities=(QueryCapability.LITERATURE,),
    )
    search_ids = {provider.descriptor.id for provider in search_providers}
    literature_ids = {provider.descriptor.id for provider in literature_providers}

    assert not expected.keys() & search_ids
    assert "pubmed" in literature_ids


@pytest.mark.asyncio
async def test_chembl_provider_keeps_mechanisms_when_activity_fails() -> None:
    class FakeClient:
        async def search_molecules(
            self, query: str, limit: int
        ) -> list[dict[str, Any]]:
            assert query == "warfarin"
            assert limit == 2
            return [{"chembl_id": "CHEMBL1464"}]

        async def get_mechanisms(
            self, chembl_id: str, limit: int
        ) -> list[dict[str, Any]]:
            assert chembl_id == "CHEMBL1464"
            assert limit == 2
            return [{"action_type": "INHIBITOR"}]

        async def get_activities(
            self, chembl_id: str, limit: int
        ) -> list[dict[str, Any]]:
            assert chembl_id == "CHEMBL1464"
            assert limit == 2
            raise RuntimeError("activity endpoint unavailable")

    provider = ChEMBLKnowledgeProvider(FakeClient())  # type: ignore[arg-type]
    result = await provider.query(
        ProviderQuery(
            text="warfarin",
            capabilities=(QueryCapability.TARGET, QueryCapability.BIOACTIVITY),
            limit=2,
        )
    )

    assert result.status is ResponseStatus.PARTIAL
    assert result.data["mechanisms"]["CHEMBL1464"] == [{"action_type": "INHIBITOR"}]
    assert "activities" not in result.data
    assert result.warnings == ["ChEMBL activities lookup failed for CHEMBL1464"]
