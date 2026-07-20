"""Coverage and regression tests for the retained atomic service gateways."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from pharmacy_mcp.application.services.drug_info import DrugInfoService
from pharmacy_mcp.application.services.drug_search import DrugSearchService
from pharmacy_mcp.application.services.interaction import InteractionService
from pharmacy_mcp.application.services.taiwan_drug import TaiwanDrugService
from pharmacy_mcp.domain.entities.drug import Drug, DrugConcept, DrugType
from pharmacy_mcp.infrastructure.api.fda import FDAClient
from pharmacy_mcp.infrastructure.api.rxnorm import RxNormClient
from pharmacy_mcp.infrastructure.api.tfda import TFDAClient
from pharmacy_mcp.infrastructure.cache.disk_cache import CacheService


class MemoryCache:
    def __init__(self) -> None:
        self.values: dict[str, Any] = {}

    def get(self, key: str) -> Any | None:
        return self.values.get(key)

    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        del ttl
        self.values[key] = value
        return True


class FakeRxNorm:
    async def search_by_name(
        self, name: str, max_results: int = 10
    ) -> list[DrugConcept]:
        return [DrugConcept(rxcui="11289", name=name.title(), tty="IN")][:max_results]

    async def get_by_rxcui(self, rxcui: str) -> Drug | None:
        if rxcui == "missing":
            return None
        return Drug(
            rxcui=rxcui,
            name="Warfarin",
            drug_type=DrugType.INGREDIENT,
            drug_classes=["Vitamin K Antagonists"],
            atc_codes=["B01AA03"],
        )


class FakeFDA:
    async def search_drug_labels(
        self, drug_name: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        return [
            {
                "openfda": {
                    "brand_name": [drug_name.title()],
                    "generic_name": [drug_name],
                    "manufacturer_name": ["Example Pharma"],
                }
            }
        ][:limit]

    async def get_drug_label_sections(self, drug_name: str) -> dict[str, Any] | None:
        if drug_name == "missing":
            return None
        return {
            "dosage_and_administration": ["Individualize dose"],
            "indications_and_usage": ["Anticoagulation"],
            "route": ["ORAL"],
            "pediatric_use": [],
            "geriatric_use": ["Monitor closely"],
            "contraindications": ["Pregnancy"],
            "warnings": ["Bleeding"],
            "warnings_and_cautions": ["Monitor INR"],
            "adverse_reactions": ["Hemorrhage"],
            "overdosage": ["Vitamin K"],
            "clinical_pharmacology": ["Anticoagulant"],
            "mechanism_of_action": ["Vitamin K antagonist"],
            "pharmacokinetics": ["Oral absorption"],
        }

    async def get_drug_interactions_from_label(
        self, drug_name: str
    ) -> dict[str, Any] | None:
        return {
            "drug_interactions": [f"{drug_name} with aspirin may increase bleeding"],
            "precautions": ["Take consistently with food; avoid alcohol"],
            "contraindications": [],
            "warnings": ["Bleeding"],
        }


def test_disk_cache_lifecycle_and_get_or_set(tmp_path: Path) -> None:
    cache = CacheService(str(tmp_path / "cache"))

    assert cache.get("missing") is None
    assert cache.set("drug", {"name": "warfarin"}, ttl=30)
    assert cache.get("drug") == {"name": "warfarin"}
    assert "drug" in cache
    assert cache.get_or_set("drug", lambda: {"name": "other"})["name"] == "warfarin"
    assert cache.get_or_set("new", lambda: ["aspirin"]) == ["aspirin"]
    assert cache.delete("drug")
    cache.clear()
    cache.close()
    cache.close()


@pytest.mark.asyncio
async def test_openfda_client_projects_labels_events_and_sections(
    respx_mock: respx.MockRouter,
) -> None:
    base_url = "https://fda.example"
    label = {
        "openfda": {
            "brand_name": ["Coumadin"],
            "generic_name": ["warfarin"],
            "manufacturer_name": ["Example"],
            "route": ["ORAL"],
            "substance_name": ["WARFARIN SODIUM"],
        },
        "drug_interactions": ["aspirin"],
        "contraindications": ["pregnancy"],
        "warnings": ["bleeding"],
        "precautions": ["monitor"],
        "dosage_and_administration": ["individualize"],
    }
    respx_mock.get(f"{base_url}/drug/label.json").mock(
        return_value=httpx.Response(200, json={"results": [label]})
    )
    respx_mock.get(f"{base_url}/drug/event.json").mock(
        return_value=httpx.Response(200, json={"results": [{"safetyreportid": "1"}]})
    )
    respx_mock.get(f"{base_url}/drug/ndc.json").mock(
        return_value=httpx.Response(200, json={"results": [{"product_ndc": "1"}]})
    )
    respx_mock.get(f"{base_url}/drug/enforcement.json").mock(
        return_value=httpx.Response(200, json={"results": [{"recall_number": "D-1"}]})
    )
    approval_route = respx_mock.get(f"{base_url}/drug/drugsfda.json").mock(
        return_value=httpx.Response(
            200, json={"results": [{"application_number": "NDA1"}]}
        )
    )
    respx_mock.get(f"{base_url}/drug/orangebook.json").mock(
        return_value=httpx.Response(
            200, json={"results": [{"approval_date": "19970326"}]}
        )
    )
    respx_mock.get(f"{base_url}/drug/shortages.json").mock(
        return_value=httpx.Response(200, json={"results": [{"status": "Current"}]})
    )
    client = FDAClient(base_url)

    assert (await client.search_drug_labels("warfarin"))[0]["openfda"]
    assert (await client.get_adverse_events("warfarin"))[0]["safetyreportid"] == "1"
    assert (await client.search_ndc("warfarin"))[0]["product_ndc"] == "1"
    assert (await client.search_recalls("warfarin"))[0]["recall_number"] == "D-1"
    assert (await client.search_approvals('warfarin "sodium"', 100))[0][
        "application_number"
    ] == "NDA1"
    assert approval_route.calls.last.request.url.params["limit"] == "99"
    assert '\\"sodium\\"' in approval_route.calls.last.request.url.params["search"]
    assert (await client.search_orange_book("warfarin"))[0]["approval_date"] == (
        "19970326"
    )
    assert (await client.search_shortages("warfarin"))[0]["status"] == "Current"
    assert (await client.get_drug_interactions_from_label("warfarin"))["warnings"] == [
        "bleeding"
    ]
    assert (await client.get_drug_label_sections("warfarin"))["brand_name"] == [
        "Coumadin"
    ]


@pytest.mark.asyncio
async def test_openfda_client_handles_missing_and_malformed_results(
    respx_mock: respx.MockRouter,
) -> None:
    base_url = "https://fda-empty.example"
    label_route = respx_mock.get(f"{base_url}/drug/label.json").mock(
        return_value=httpx.Response(404)
    )
    event_route = respx_mock.get(f"{base_url}/drug/event.json").mock(
        return_value=httpx.Response(200, json={"results": "invalid"})
    )
    client = FDAClient(base_url)

    assert await client.search_drug_labels("missing") == []
    assert await client.get_adverse_events("missing") == []
    label_route.mock(return_value=httpx.Response(200, json=[]))
    event_route.mock(return_value=httpx.Response(200, json=[]))
    assert await client.search_drug_labels("missing") == []
    assert await client.get_adverse_events("missing") == []


@pytest.mark.asyncio
async def test_rxnorm_client_search_detail_classes_and_types(
    respx_mock: respx.MockRouter,
) -> None:
    base_url = "https://rx.example"
    respx_mock.get(f"{base_url}/drugs.json").mock(
        return_value=httpx.Response(
            200,
            json={
                "drugGroup": {
                    "conceptGroup": [
                        {
                            "conceptProperties": [
                                {
                                    "rxcui": "11289",
                                    "name": "warfarin",
                                    "synonym": "warfarin sodium",
                                    "tty": "IN",
                                },
                                {"rxcui": "2", "name": "Coumadin", "tty": "BN"},
                            ]
                        }
                    ]
                }
            },
        )
    )
    respx_mock.get(f"{base_url}/rxcui/11289/properties.json").mock(
        return_value=httpx.Response(
            200, json={"properties": {"name": "warfarin", "tty": "IN"}}
        )
    )
    respx_mock.get(f"{base_url}/rxclass/class/byRxcui.json").mock(
        return_value=httpx.Response(
            200,
            json={
                "rxclassDrugInfoList": {
                    "rxclassDrugInfo": [
                        {
                            "rxclassMinConceptItem": {
                                "classId": "N1",
                                "className": "Anticoagulants",
                                "classType": "MOA",
                            },
                            "rela": "has_MoA",
                            "relaSource": "MEDRT",
                        },
                        {
                            "rxclassMinConceptItem": {
                                "classId": "N1",
                                "className": "Anticoagulants",
                                "classType": "MOA",
                            },
                            "rela": "has_MoA",
                            "relaSource": "MEDRT",
                        },
                    ]
                }
            },
        )
    )
    respx_mock.get(f"{base_url}/rxcui/missing/properties.json").mock(
        return_value=httpx.Response(404)
    )
    client = RxNormClient(base_url)

    concepts = await client.search_by_name("warfarin", max_results=1)
    drug = await client.get_by_rxcui("11289")
    assert len(concepts) == 1
    assert drug is not None and drug.drug_type is DrugType.INGREDIENT
    assert drug.drug_classes == ["Anticoagulants"]
    assert await client.get_drug_classes("11289") == ["Anticoagulants"]
    memberships = await client.get_drug_class_memberships("11289")
    assert memberships == [
        {
            "class_id": "N1",
            "class_name": "Anticoagulants",
            "class_type": "MOA",
            "relation": "has_MoA",
            "relation_source": "MEDRT",
        }
    ]
    assert await client.get_by_rxcui("missing") is None
    assert await client.get_interactions("11289") == []
    assert client._parse_drug_type("BN") is DrugType.BRAND
    assert client._parse_drug_type("SCD") is DrugType.GENERIC


@pytest.mark.asyncio
async def test_tfda_client_fetch_search_and_statistics(
    respx_mock: respx.MockRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active_url = "https://tfda.example/active"
    all_url = "https://tfda.example/all"
    monkeypatch.setattr(TFDAClient, "ACTIVE_PERMITS_JSON_URL", active_url)
    monkeypatch.setattr(TFDAClient, "DRUG_PERMITS_JSON_URL", all_url)
    active = [
        {
            "許可證字號": "A1",
            "中文品名": "華法林",
            "英文品名": "WARFARIN TABLETS",
            "主成分略述": "WARFARIN SODIUM",
            "製造廠名稱": "EXAMPLE PHARMA",
            "申請商名稱": "EXAMPLE",
            "劑型": "錠劑",
        }
    ]
    respx_mock.get(active_url).mock(return_value=httpx.Response(200, json=active))
    respx_mock.get(all_url).mock(
        return_value=httpx.Response(
            200, json=[*active, {**active[0], "許可證字號": "A2"}]
        )
    )
    client = TFDAClient(MemoryCache())  # type: ignore[arg-type]

    assert (await client.search_drug_by_name("warfarin"))[0]["permit_number"] == "A1"
    assert (await client.search_drug_by_ingredient("sodium"))[0]["source"] == "TFDA"
    assert (await client.search_drug_by_manufacturer("example"))[0]["english_name"]
    assert (await client.search_drug_by_permit_number("A2"))["permit_number"] == "A2"
    stats = await client.get_drug_statistics()
    assert stats["total_permits"] == 2
    assert stats["active_permits"] == 1


@pytest.mark.asyncio
async def test_atomic_search_and_info_services_with_cache() -> None:
    cache = MemoryCache()
    search = DrugSearchService(FakeRxNorm(), FakeFDA(), cache)
    info = DrugInfoService(FakeRxNorm(), FakeFDA(), cache)

    search_result = await search.search("warfarin")
    assert search_result["total_count"] == 2
    assert await search.search("warfarin") == search_result
    assert (await search.search_by_rxcui("11289"))["atc_codes"] == ["B01AA03"]
    assert await search.search_by_rxcui("missing") is None
    assert (await search.autocomplete("warf"))[0].rxcui == "11289"

    full = await info.get_full_info("warfarin")
    assert full["rxnorm"]["rxcui"] == "11289"
    assert await info.get_full_info("warfarin") == full
    assert (await info.get_dosage_info("warfarin"))["route"] == ["ORAL"]
    assert (await info.get_warnings("warfarin"))["warnings"] == ["Bleeding"]
    assert (await info.get_pharmacology("warfarin"))["mechanism_of_action"]
    assert (await info.get_dosage_info("missing"))["dosage_info"] is None


@pytest.mark.asyncio
async def test_atomic_interaction_service_covers_pair_multi_food_and_profile() -> None:
    service = InteractionService(FakeRxNorm(), FakeFDA(), MemoryCache())

    pair = await service.check_drug_drug_interaction("warfarin", "aspirin")
    assert pair["has_interaction"] is True
    assert await service.check_drug_drug_interaction("warfarin", "aspirin") == pair
    multi = await service.check_multi_drug_interactions(
        ["warfarin", "aspirin", "ibuprofen"]
    )
    assert multi["pairs_checked"] == 3
    assert (await service.check_multi_drug_interactions(["warfarin"]))["error"]
    food = await service.check_food_drug_interaction("warfarin")
    assert food["has_food_interactions"] is True
    profile = await service.get_all_interactions("warfarin")
    assert profile["drug_interactions"]
    assert await service.get_all_interactions("warfarin") == profile


class FakeTFDA:
    async def search_drug_by_permit_number(self, query: str) -> dict[str, Any] | None:
        return {"permit_number": query} if query != "missing" else None

    async def search_drug_by_ingredient(
        self, query: str, limit: int
    ) -> list[dict[str, Any]]:
        return [{"ingredient": query}][:limit]

    async def search_drug_by_manufacturer(
        self, query: str, limit: int
    ) -> list[dict[str, Any]]:
        return [{"manufacturer": query}][:limit]

    async def search_drug_by_name(self, query: str, limit: int) -> list[dict[str, Any]]:
        return [{"name": query}][:limit]

    async def get_drug_statistics(self) -> dict[str, Any]:
        return {"active_permits": 1}


class FakeNHI:
    async def check_coverage(self, drug_name: str) -> dict[str, Any]:
        return {"is_covered": drug_name == "covered"}

    async def get_drug_price(self, nhi_code: str) -> dict[str, Any] | None:
        return {"nhi_code": nhi_code, "price": 5.5} if nhi_code != "missing" else None

    async def search_by_drug_name(
        self, drug_name: str, limit: int
    ) -> list[dict[str, Any]]:
        return [{"name": drug_name}][:limit]

    def get_index_status(self) -> dict[str, Any]:
        return {"ready": True}

    async def get_prior_authorization_drugs(self) -> list[dict[str, Any]]:
        return [{"category": "oncology"}]


@pytest.mark.asyncio
async def test_taiwan_service_routes_all_atomic_query_modes() -> None:
    service = TaiwanDrugService(FakeTFDA(), FakeNHI())  # type: ignore[arg-type]

    for search_type in ("name", "ingredient", "manufacturer", "permit_number"):
        result = await service.search_tfda_drug("warfarin", search_type=search_type)
        assert result["result_count"] == 1
    assert (await service.search_tfda_drug("missing", search_type="permit_number"))[
        "result_count"
    ] == 0
    assert (await service.get_nhi_coverage("warfarin"))["found"] is True
    assert (await service.get_nhi_coverage("covered"))["found"] is True
    assert (await service.get_nhi_drug_price("A022664100"))["found"] is True
    assert (await service.get_nhi_drug_price("missing"))["found"] is False
    assert (await service.search_nhi_drugs("warfarin"))["index"]["ready"] is True
    assert service.get_nhi_data_status()["ready"] is True
    assert service.translate_drug_name("warfarin")["found"] is True
    assert service.translate_drug_name("unknown_xyz")["found"] is False
    assert (await service.get_prior_authorization_drugs())["specific_drugs"]
    assert (await service.get_tfda_statistics())["statistics"]["active_permits"] == 1
    assert service.list_available_translations()["count"] > 100
    assert service.list_nhi_coverage_rules()["count"] > 50
