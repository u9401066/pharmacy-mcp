"""Application service path tests with deterministic fakes."""

from pharmacy_mcp.application.services import drug_info as drug_info_module
from pharmacy_mcp.application.services.drug_info import DrugInfoService
from pharmacy_mcp.application.services.drug_search import DrugSearchService
from pharmacy_mcp.application.services.interaction import InteractionService
from pharmacy_mcp.domain.entities.drug import Drug, DrugConcept, DrugType


class MemoryCache:
    """Small cache fake matching the CacheService surface used by services."""

    def __init__(self):
        self.items = {}

    def get(self, key):
        return self.items.get(key)

    def set(self, key, value, *_, **__):
        self.items[key] = value
        return True


class FakeRxNormClient:
    async def search_by_name(self, query, max_results=10):
        return [
            DrugConcept(
                rxcui="11289",
                name=query.title(),
                synonym=f"{query} sodium",
                tty="IN",
            )
        ][:max_results]

    async def get_by_rxcui(self, rxcui):
        if rxcui == "missing":
            return None
        return Drug(
            rxcui=rxcui,
            name="Warfarin",
            drug_type=DrugType.INGREDIENT,
            atc_codes=["B01AA03"],
            drug_classes=["anticoagulant"],
        )


class FakeFDAClient:
    def __init__(self, *, label=None, interactions=None):
        self.label = label if label is not None else self.default_label()
        self.interactions = (
            interactions if interactions is not None else self.default_interactions()
        )

    @staticmethod
    def default_label():
        return {
            "dosage_and_administration": ["Dose by INR"],
            "indications_and_usage": ["Anticoagulation"],
            "route": ["oral"],
            "pediatric_use": ["Use individualized dosing"],
            "geriatric_use": ["Monitor closely"],
            "contraindications": ["Active bleeding"],
            "warnings": ["Bleeding risk"],
            "warnings_and_cautions": ["Monitor INR"],
            "adverse_reactions": ["Bleeding"],
            "overdosage": ["Vitamin K"],
            "clinical_pharmacology": ["Vitamin K antagonist"],
            "mechanism_of_action": ["VKORC1 inhibition"],
            "pharmacokinetics": ["CYP2C9 metabolism"],
        }

    @staticmethod
    def default_interactions():
        return {
            "drug_interactions": [
                "Aspirin may increase bleeding risk with warfarin.",
                "Avoid grapefruit with some CYP3A substrates.",
            ],
            "precautions": ["Take with food if stomach upset occurs."],
            "contraindications": ["Active pathological bleeding"],
            "warnings": ["Serious bleeding can occur."],
        }

    async def search_drug_labels(self, query, max_results=10):
        return [
            {
                "openfda": {
                    "brand_name": [query.title()],
                    "generic_name": [query.lower()],
                    "manufacturer_name": ["Example Pharma"],
                }
            }
        ][:max_results]

    async def get_drug_label_sections(self, _drug_name):
        return self.label

    async def get_drug_interactions_from_label(self, _drug_name):
        return self.interactions


async def test_drug_search_combines_sources_and_uses_cache():
    service = DrugSearchService(
        rxnorm_client=FakeRxNormClient(),
        fda_client=FakeFDAClient(),
        cache=MemoryCache(),
    )

    result = await service.search("warfarin", max_results=3)
    cached_result = await service.search("warfarin", max_results=3)
    by_rxcui = await service.search_by_rxcui("11289")
    missing = await service.search_by_rxcui("missing")
    suggestions = await service.autocomplete("warf", max_results=1)

    assert result["total_count"] == 2
    assert result["rxnorm"][0]["rxcui"] == "11289"
    assert result["fda"][0]["manufacturer"] == ["Example Pharma"]
    assert cached_result == result
    assert by_rxcui["atc_codes"] == ["B01AA03"]
    assert missing is None
    assert suggestions[0].name == "Warf"


async def test_drug_info_builds_full_label_taiwan_and_section_views(monkeypatch):
    monkeypatch.setattr(
        drug_info_module,
        "translate_drug_name",
        lambda _drug_name: {
            "english": "Warfarin",
            "chinese_generic": "華法林",
            "chinese_brand": ["可邁丁"],
            "category": "anticoagulant",
            "nickname": "老鼠藥",
        },
    )
    monkeypatch.setattr(
        drug_info_module,
        "get_nhi_coverage_info",
        lambda _drug_name: {
            "is_covered": True,
            "coverage_type": "general",
            "indications": ["AF"],
            "restrictions": ["INR monitoring"],
            "prior_authorization": False,
            "nhi_codes": ["BC123"],
        },
    )
    service = DrugInfoService(
        rxnorm_client=FakeRxNormClient(),
        fda_client=FakeFDAClient(),
        cache=MemoryCache(),
    )

    full = await service.get_full_info("warfarin")
    cached_full = await service.get_full_info("warfarin")
    dosage = await service.get_dosage_info("warfarin")
    warnings = await service.get_warnings("warfarin")
    pharmacology = await service.get_pharmacology("warfarin")

    assert full["rxnorm"]["drug_type"] == "ingredient"
    assert full["taiwan"]["translation"]["nickname"] == "老鼠藥"
    assert full["taiwan"]["nhi"]["is_covered"] is True
    assert cached_full == full
    assert dosage["route"] == ["oral"]
    assert warnings["contraindications"] == ["Active bleeding"]
    assert pharmacology["mechanism_of_action"] == ["VKORC1 inhibition"]


async def test_drug_info_handles_missing_label_sections(monkeypatch):
    monkeypatch.setattr(drug_info_module, "translate_drug_name", lambda _name: None)
    monkeypatch.setattr(
        drug_info_module, "get_nhi_coverage_info", lambda _name: None
    )
    service = DrugInfoService(
        rxnorm_client=FakeRxNormClient(),
        fda_client=FakeFDAClient(label={}),
        cache=MemoryCache(),
    )

    full = await service.get_full_info("unknown")
    dosage = await service.get_dosage_info("unknown")
    warnings = await service.get_warnings("unknown")
    pharmacology = await service.get_pharmacology("unknown")

    assert full["taiwan"] is None
    assert dosage["dosage_info"] is None
    assert warnings["warnings"] is None
    assert pharmacology["pharmacology"] is None


async def test_interaction_service_checks_local_fda_food_and_all_paths():
    service = InteractionService(
        fda_client=FakeFDAClient(),
        cache=MemoryCache(),
    )

    ddi = await service.check_drug_drug_interaction("warfarin", "aspirin")
    cached_ddi = await service.check_drug_drug_interaction("warfarin", "aspirin")
    too_few = await service.check_multi_drug_interactions(["warfarin"])
    multi = await service.check_multi_drug_interactions(
        ["warfarin", "aspirin", "ibuprofen"]
    )
    food = await service.check_food_drug_interaction("simvastatin")
    all_interactions = await service.get_all_interactions("warfarin")
    cached_all = await service.get_all_interactions("warfarin")

    assert ddi["has_interaction"] is True
    assert ddi["fda_mentions_interaction"] is True
    assert ddi["not_for_direct_clinical_decision"] is True
    assert "recommendation" not in ddi["interactions"][0]
    assert "Reduce" not in ddi["interactions"][0]["management_consideration"]
    assert ddi["source_label_excerpts"][0]["section"] == "drug_interactions"
    assert ddi["source_label_excerpts"][0]["source"] == "FDA label"
    assert cached_ddi == ddi
    assert too_few["error"] == "Need at least 2 drugs"
    assert multi["pairs_checked"] == 3
    assert multi["total_interactions"] >= 2
    assert food["has_food_interactions"] is True
    assert food["food_interactions"][0]["food"] == "Grapefruit"
    assert "recommendation" not in food["food_interactions"][0]
    assert food["source_label_excerpts"][0]["section"] == "drug_interactions"
    assert all_interactions["drug_interactions"]
    assert "recommendation" not in all_interactions["drug_interactions"][0]
    assert "Reduce" not in all_interactions["drug_interactions"][0][
        "management_consideration"
    ]
    assert "contraindications" not in all_interactions
    assert any(
        excerpt["section"] == "contraindications"
        for excerpt in all_interactions["source_label_excerpts"]
    )
    assert cached_all == all_interactions


async def test_interaction_service_ignores_legacy_cache_without_safety_contract():
    """Old cache namespaces must not bypass the sanitized interaction schema."""
    cache = MemoryCache()
    service = InteractionService(
        fda_client=FakeFDAClient(),
        cache=cache,
    )
    old_ddi_key = service._cache_key("ddi", *sorted(["warfarin", "aspirin"]))
    old_all_key = service._cache_key("all_interactions", "warfarin")
    cache.set(
        old_ddi_key,
        {
            "has_interaction": True,
            "interactions": [{"recommendation": "Reduce dose immediately"}],
        },
    )
    cache.set(
        old_all_key,
        {
            "drug_interactions": [{"recommendation": "Avoid combination"}],
        },
    )

    ddi = await service.check_drug_drug_interaction("warfarin", "aspirin")
    all_interactions = await service.get_all_interactions("warfarin")

    assert ddi["not_for_direct_clinical_decision"] is True
    assert "recommendation" not in ddi["interactions"][0]
    assert "recommendation" not in all_interactions["drug_interactions"][0]


async def test_interaction_service_rejects_blank_drug_names():
    """Blank drug names should not match every local interaction row."""
    service = InteractionService(
        fda_client=FakeFDAClient(),
        cache=MemoryCache(),
    )

    ddi = await service.check_drug_drug_interaction("   ", "aspirin")
    multi = await service.check_multi_drug_interactions(["warfarin", "   "])
    food = await service.check_food_drug_interaction("   ")
    all_interactions = await service.get_all_interactions("   ")

    assert ddi["has_interaction"] is False
    assert ddi["error"] == "Drug names cannot be blank"
    assert multi["error"] == "Drug names cannot be blank"
    assert food["has_food_interactions"] is False
    assert food["error"] == "Drug name cannot be blank"
    assert all_interactions["error"] == "Drug name cannot be blank"


async def test_multi_drug_interactions_handles_fda_only_hit_without_local_severity():
    """FDA-only interaction hits should not crash severity sorting."""
    service = InteractionService(
        fda_client=FakeFDAClient(
            interactions={
                "drug_interactions": [
                    "Unknown-b may increase exposure to unknown-a in label text."
                ],
                "precautions": [],
                "contraindications": [],
                "warnings": [],
            }
        ),
        cache=MemoryCache(),
    )

    result = await service.check_multi_drug_interactions(["unknown-a", "unknown-b"])

    assert result["total_interactions"] == 1
    assert result["interactions"][0]["interactions"] == []
    assert result["interactions"][0]["fda_mentions_interaction"] is True
    assert result["interactions"][0]["source_label_excerpts"][0]["source"] == "FDA label"
    assert result["not_for_direct_clinical_decision"] is True
