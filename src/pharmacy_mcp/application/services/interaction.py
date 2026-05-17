"""Drug interaction service."""

import hashlib
import re
from typing import Any

from pharmacy_mcp.application.services.simulation import SimulationService
from pharmacy_mcp.config import settings
from pharmacy_mcp.infrastructure.api.fda import FDAClient
from pharmacy_mcp.infrastructure.api.rxnorm import RxNormClient
from pharmacy_mcp.infrastructure.cache.disk_cache import CacheService

# Common drug-drug interactions database
# Note: RxNorm Drug Interaction API was discontinued by NLM in 2025
# This local database provides basic interaction checking
DRUG_DRUG_INTERACTIONS = {
    ("warfarin", "aspirin"): {
        "severity": "high",
        "description": "Increased risk of bleeding. Aspirin inhibits platelet function and warfarin inhibits clotting factors.",
        "recommendation": "Avoid combination unless specifically indicated. Monitor for signs of bleeding.",
    },
    ("warfarin", "ibuprofen"): {
        "severity": "high",
        "description": "NSAIDs increase risk of GI bleeding and may enhance anticoagulant effect.",
        "recommendation": "Avoid combination. Use acetaminophen for pain if needed.",
    },
    ("warfarin", "naproxen"): {
        "severity": "high",
        "description": "NSAIDs increase risk of GI bleeding and may enhance anticoagulant effect.",
        "recommendation": "Avoid combination. Use acetaminophen for pain if needed.",
    },
    ("warfarin", "fluconazole"): {
        "severity": "high",
        "description": "Fluconazole inhibits CYP2C9, significantly increasing warfarin levels.",
        "recommendation": "Reduce warfarin dose and monitor INR closely.",
    },
    ("warfarin", "metronidazole"): {
        "severity": "high",
        "description": "Metronidazole inhibits warfarin metabolism, increasing anticoagulant effect.",
        "recommendation": "Monitor INR closely; may need warfarin dose reduction.",
    },
    ("warfarin", "amiodarone"): {
        "severity": "high",
        "description": "Amiodarone significantly inhibits warfarin metabolism.",
        "recommendation": "Reduce warfarin dose by 30-50% and monitor INR closely.",
    },
    ("metformin", "alcohol"): {
        "severity": "high",
        "description": "Alcohol increases risk of lactic acidosis with metformin.",
        "recommendation": "Limit alcohol consumption; avoid binge drinking.",
    },
    ("metformin", "contrast dye"): {
        "severity": "high",
        "description": "Iodinated contrast can cause acute kidney injury, increasing metformin toxicity risk.",
        "recommendation": "Hold metformin before and 48 hours after contrast procedures.",
    },
    ("lisinopril", "potassium"): {
        "severity": "moderate",
        "description": "ACE inhibitors can increase potassium levels; supplements may cause hyperkalemia.",
        "recommendation": "Monitor potassium levels; avoid potassium supplements unless prescribed.",
    },
    ("lisinopril", "spironolactone"): {
        "severity": "moderate",
        "description": "Both drugs can increase potassium levels, risking hyperkalemia.",
        "recommendation": "Monitor potassium levels closely.",
    },
    ("simvastatin", "amiodarone"): {
        "severity": "high",
        "description": "Amiodarone increases simvastatin levels, increasing risk of myopathy/rhabdomyolysis.",
        "recommendation": "Do not exceed simvastatin 20mg daily with amiodarone.",
    },
    ("simvastatin", "amlodipine"): {
        "severity": "moderate",
        "description": "Amlodipine increases simvastatin levels.",
        "recommendation": "Do not exceed simvastatin 20mg daily with amlodipine.",
    },
    ("simvastatin", "diltiazem"): {
        "severity": "high",
        "description": "Diltiazem significantly increases simvastatin levels.",
        "recommendation": "Do not exceed simvastatin 10mg daily with diltiazem.",
    },
    ("atorvastatin", "clarithromycin"): {
        "severity": "high",
        "description": "Clarithromycin inhibits CYP3A4, increasing statin levels and myopathy risk.",
        "recommendation": "Avoid combination or use alternative antibiotic.",
    },
    ("clopidogrel", "omeprazole"): {
        "severity": "moderate",
        "description": "Omeprazole may reduce clopidogrel's antiplatelet effect via CYP2C19 inhibition.",
        "recommendation": "Consider pantoprazole as alternative PPI.",
    },
    ("clopidogrel", "esomeprazole"): {
        "severity": "moderate",
        "description": "Esomeprazole may reduce clopidogrel's antiplatelet effect via CYP2C19 inhibition.",
        "recommendation": "Consider pantoprazole as alternative PPI.",
    },
    ("digoxin", "amiodarone"): {
        "severity": "high",
        "description": "Amiodarone increases digoxin levels by reducing clearance.",
        "recommendation": "Reduce digoxin dose by 50% and monitor levels.",
    },
    ("digoxin", "verapamil"): {
        "severity": "high",
        "description": "Verapamil increases digoxin levels and enhances AV nodal blocking effects.",
        "recommendation": "Reduce digoxin dose and monitor levels and heart rate.",
    },
    ("sildenafil", "nitrates"): {
        "severity": "contraindicated",
        "description": "Life-threatening hypotension can occur.",
        "recommendation": "CONTRAINDICATED - Do not use together.",
    },
    ("tadalafil", "nitrates"): {
        "severity": "contraindicated",
        "description": "Life-threatening hypotension can occur.",
        "recommendation": "CONTRAINDICATED - Do not use together.",
    },
    ("maois", "ssris"): {
        "severity": "contraindicated",
        "description": "Risk of serotonin syndrome, potentially fatal.",
        "recommendation": "CONTRAINDICATED - Allow washout period between medications.",
    },
    ("fluoxetine", "maois"): {
        "severity": "contraindicated",
        "description": "Risk of serotonin syndrome, potentially fatal.",
        "recommendation": "CONTRAINDICATED - Allow 5 weeks washout after fluoxetine.",
    },
    ("tramadol", "ssris"): {
        "severity": "high",
        "description": "Increased risk of serotonin syndrome and seizures.",
        "recommendation": "Use with caution; monitor for serotonin syndrome symptoms.",
    },
    ("methotrexate", "nsaids"): {
        "severity": "high",
        "description": "NSAIDs reduce methotrexate clearance, increasing toxicity risk.",
        "recommendation": "Avoid combination, especially with high-dose methotrexate.",
    },
    ("lithium", "nsaids"): {
        "severity": "high",
        "description": "NSAIDs reduce lithium excretion, increasing levels and toxicity risk.",
        "recommendation": "Monitor lithium levels closely if NSAID is necessary.",
    },
    ("lithium", "lisinopril"): {
        "severity": "high",
        "description": "ACE inhibitors reduce lithium excretion, increasing levels.",
        "recommendation": "Monitor lithium levels closely.",
    },
    ("theophylline", "ciprofloxacin"): {
        "severity": "high",
        "description": "Ciprofloxacin inhibits theophylline metabolism, increasing levels.",
        "recommendation": "Monitor theophylline levels; may need dose reduction.",
    },
    ("aspirin", "ibuprofen"): {
        "severity": "moderate",
        "description": "Ibuprofen may interfere with aspirin's cardioprotective antiplatelet effect.",
        "recommendation": "Take aspirin at least 30 minutes before ibuprofen.",
    },
}


# Common food-drug interactions database
FOOD_DRUG_INTERACTIONS = {
    "warfarin": [
        {
            "food": "Vitamin K rich foods (spinach, kale, broccoli)",
            "effect": "Decreased anticoagulant effect",
            "severity": "high",
            "recommendation": "Maintain consistent vitamin K intake; monitor INR",
        },
        {
            "food": "Grapefruit",
            "effect": "Increased bleeding risk",
            "severity": "moderate",
            "recommendation": "Avoid or limit grapefruit consumption",
        },
        {
            "food": "Alcohol",
            "effect": "Increased bleeding risk and liver damage",
            "severity": "high",
            "recommendation": "Limit alcohol consumption",
        },
    ],
    "metformin": [
        {
            "food": "Alcohol",
            "effect": "Increased risk of lactic acidosis",
            "severity": "high",
            "recommendation": "Avoid excessive alcohol consumption",
        },
    ],
    "simvastatin": [
        {
            "food": "Grapefruit",
            "effect": "Increased drug levels, risk of muscle damage",
            "severity": "high",
            "recommendation": "Avoid grapefruit and grapefruit juice",
        },
    ],
    "atorvastatin": [
        {
            "food": "Grapefruit",
            "effect": "Increased drug levels, risk of muscle damage",
            "severity": "moderate",
            "recommendation": "Limit grapefruit consumption",
        },
    ],
    "levothyroxine": [
        {
            "food": "Calcium-rich foods, iron supplements",
            "effect": "Decreased drug absorption",
            "severity": "moderate",
            "recommendation": "Take on empty stomach, 4 hours apart from calcium/iron",
        },
        {
            "food": "Soy products",
            "effect": "Decreased drug absorption",
            "severity": "moderate",
            "recommendation": "Space consumption from medication",
        },
    ],
    "ciprofloxacin": [
        {
            "food": "Dairy products, calcium-fortified foods",
            "effect": "Decreased drug absorption",
            "severity": "moderate",
            "recommendation": "Take 2 hours before or 6 hours after dairy",
        },
    ],
    "tetracycline": [
        {
            "food": "Dairy products",
            "effect": "Decreased drug absorption",
            "severity": "high",
            "recommendation": "Avoid dairy 2 hours before and after taking",
        },
    ],
    "maois": [  # monoamine oxidase inhibitors
        {
            "food": "Tyramine-rich foods (aged cheese, cured meats, fermented foods)",
            "effect": "Hypertensive crisis",
            "severity": "critical",
            "recommendation": "Strict avoidance of tyramine-rich foods",
        },
    ],
    "amlodipine": [
        {
            "food": "Grapefruit",
            "effect": "Increased drug levels, excessive blood pressure lowering",
            "severity": "moderate",
            "recommendation": "Limit grapefruit consumption",
        },
    ],
}


INTERACTION_MECHANISMS = {
    tuple(sorted(("warfarin", "fluconazole"))): {
        "pathway": "CYP2C9",
        "effect": "inhibition",
        "interaction_type": "cyp_reversible_inhibition",
        "description": "Fluconazole can inhibit CYP2C9-mediated warfarin clearance, increasing exposure and anticoagulant effect.",
        "substrate": "warfarin",
        "perpetrator": "fluconazole",
        "required_parameters": [
            "cl_total",
            "fm",
            "inhibitor_concentration",
            "ki",
        ],
    },
    tuple(sorted(("simvastatin", "clarithromycin"))): {
        "pathway": "CYP3A4",
        "effect": "inhibition",
        "interaction_type": "cyp_reversible_inhibition",
        "description": "Clarithromycin can inhibit CYP3A4-mediated simvastatin clearance, increasing exposure and myopathy risk.",
        "substrate": "simvastatin",
        "perpetrator": "clarithromycin",
        "required_parameters": [
            "cl_total",
            "fm",
            "inhibitor_concentration",
            "ki",
        ],
    },
    tuple(sorted(("atorvastatin", "clarithromycin"))): {
        "pathway": "CYP3A4",
        "effect": "inhibition",
        "interaction_type": "cyp_reversible_inhibition",
        "description": "Clarithromycin can inhibit CYP3A4-mediated atorvastatin clearance, increasing exposure and muscle toxicity risk.",
        "substrate": "atorvastatin",
        "perpetrator": "clarithromycin",
        "required_parameters": [
            "cl_total",
            "fm",
            "inhibitor_concentration",
            "ki",
        ],
    },
}

SAFETY_NOTE = (
    "Educational interaction screening only. Verify against current product "
    "labeling, patient-specific factors, and institutional protocols before any "
    "clinical action."
)
CACHE_SCHEMA_VERSION = "v2"
MIN_PARTIAL_MATCH_LENGTH = 3


class InteractionService:
    """Service for checking drug-drug and food-drug interactions."""

    def __init__(
        self,
        rxnorm_client: RxNormClient | None = None,
        fda_client: FDAClient | None = None,
        cache: CacheService | None = None,
        simulation_service: SimulationService | None = None,
    ):
        self.rxnorm = rxnorm_client or RxNormClient()
        self.fda = fda_client or FDAClient()
        self.cache = cache or CacheService()
        self.simulation = simulation_service or SimulationService()

    async def check_drug_drug_interaction(
        self,
        drug1: str,
        drug2: str,
    ) -> dict[str, Any]:
        """
        Check interaction between two drugs.

        Note: Uses local interaction database as RxNorm Drug Interaction API
        was discontinued by NLM in 2025.

        Args:
            drug1: First drug name
            drug2: Second drug name

        Returns:
            Interaction information
        """
        drug1_normalized = self._normalize_drug_name(drug1)
        drug2_normalized = self._normalize_drug_name(drug2)
        if not drug1_normalized or not drug2_normalized:
            return {
                "drug1": drug1,
                "drug2": drug2,
                "interactions": [],
                "interaction_count": 0,
                "has_interaction": False,
                "error": "Drug names cannot be blank",
                **self._safety_metadata(),
            }

        cache_key = self._cache_key(
            f"ddi:{CACHE_SCHEMA_VERSION}",
            *sorted([drug1_normalized, drug2_normalized]),
        )
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # Check local database for interactions
        interactions = []

        # Try to find interaction in local database
        for (d1, d2), interaction_data in DRUG_DRUG_INTERACTIONS.items():
            # Check if either drug matches (partial match allowed)
            d1_match = self._drug_names_match(d1, drug1_normalized)
            d2_match = self._drug_names_match(d2, drug2_normalized)
            d1_match_rev = self._drug_names_match(d1, drug2_normalized)
            d2_match_rev = self._drug_names_match(d2, drug1_normalized)

            if (d1_match and d2_match) or (d1_match_rev and d2_match_rev):
                interactions.append(
                    {
                        "description": interaction_data.get("description"),
                        "severity": interaction_data.get("severity"),
                        "management_consideration": self._management_consideration(
                            str(interaction_data.get("severity", ""))
                        ),
                        "source_recommendation_note": (
                            "Original local database guidance is intentionally "
                            "summarized as a clinical review consideration."
                        ),
                        "drugs_involved": [drug1, drug2],
                    }
                )

        # Also get from FDA label for additional context
        fda_interactions = await self.fda.get_drug_interactions_from_label(drug1)
        fda_mentions_drug2 = False
        fda_context = []

        if fda_interactions:
            for text in fda_interactions.get("drug_interactions", []):
                if drug2_normalized in text.lower():
                    fda_mentions_drug2 = True
                    fda_context.append(
                        self._source_label_excerpt("drug_interactions", text)
                    )

        result = {
            "drug1": drug1,
            "drug2": drug2,
            "interactions": interactions,
            "interaction_count": len(interactions),
            "has_interaction": len(interactions) > 0 or fda_mentions_drug2,
            "fda_mentions_interaction": fda_mentions_drug2,
            "source_label_excerpts": fda_context[:2],
            "source": "local_database",
            "note": "RxNorm Drug Interaction API was discontinued by NLM in 2025. Using local database.",
            **self._safety_metadata(),
        }

        self.cache.set(cache_key, result)
        return result

    async def check_multi_drug_interactions(
        self,
        drugs: list[str],
    ) -> dict[str, Any]:
        """
        Check interactions among multiple drugs.

        Args:
            drugs: List of drug names

        Returns:
            All pairwise interactions
        """
        if len(drugs) < 2:
            return {
                "drugs": drugs,
                "interactions": [],
                "error": "Need at least 2 drugs",
                **self._safety_metadata(),
            }

        all_interactions = []
        checked_pairs = set()
        normalized_drugs = [self._normalize_drug_name(drug) for drug in drugs]
        if any(not drug for drug in normalized_drugs):
            return {
                "drugs": drugs,
                "interactions": [],
                "error": "Drug names cannot be blank",
                **self._safety_metadata(),
            }

        for i, drug1 in enumerate(drugs):
            for drug2 in drugs[i + 1 :]:
                pair = tuple(
                    sorted(
                        [
                            self._normalize_drug_name(drug1),
                            self._normalize_drug_name(drug2),
                        ]
                    )
                )
                if pair in checked_pairs:
                    continue
                checked_pairs.add(pair)

                result = await self.check_drug_drug_interaction(drug1, drug2)
                if result.get("has_interaction"):
                    all_interactions.append(result)

        # Sort by severity
        severity_order = {"contraindicated": 0, "high": 1, "moderate": 2, "low": 3}
        all_interactions.sort(key=lambda x: self._severity_rank(x, severity_order))

        return {
            "drugs": drugs,
            "interactions": all_interactions,
            "total_interactions": len(all_interactions),
            "pairs_checked": len(checked_pairs),
            **self._safety_metadata(),
        }

    async def check_food_drug_interaction(
        self,
        drug_name: str,
    ) -> dict[str, Any]:
        """
        Check food-drug interactions for a drug.

        Args:
            drug_name: Name of the drug

        Returns:
            Food interaction information
        """
        drug_normalized = self._normalize_drug_name(drug_name)
        if not drug_normalized:
            return {
                "drug_name": drug_name,
                "food_interactions": [],
                "source_label_excerpts": [],
                "has_food_interactions": False,
                "error": "Drug name cannot be blank",
                **self._safety_metadata(),
            }

        # Check local database first
        local_interactions = []
        for drug_key, interactions in FOOD_DRUG_INTERACTIONS.items():
            if self._drug_names_match(drug_key, drug_normalized):
                local_interactions.extend(
                    self._food_interaction_view(interaction)
                    for interaction in interactions
                )

        # Also get from FDA label
        fda_interactions = await self.fda.get_drug_interactions_from_label(drug_name)

        # Extract food-related warnings from FDA label
        fda_food_info = []
        if fda_interactions:
            for section in ["drug_interactions", "precautions"]:
                content = fda_interactions.get(section, [])
                for text in content:
                    text_lower = text.lower()
                    if any(
                        food in text_lower
                        for food in ["food", "meal", "grapefruit", "dairy", "alcohol"]
                    ):
                        fda_food_info.append(self._source_label_excerpt(section, text))

        return {
            "drug_name": drug_name,
            "food_interactions": local_interactions,
            "source_label_excerpts": fda_food_info,
            "has_food_interactions": len(local_interactions) > 0
            or len(fda_food_info) > 0,
            **self._safety_metadata(),
        }

    def explain_interaction_mechanism(
        self,
        drug1: str,
        drug2: str,
    ) -> dict[str, Any]:
        """Explain a supported mechanistic DDI pathway for a drug pair."""
        pair = tuple(
            sorted((self._normalize_drug_name(drug1), self._normalize_drug_name(drug2)))
        )
        mechanism = INTERACTION_MECHANISMS.get(pair)
        if mechanism is None:
            return {
                "drug1": drug1,
                "drug2": drug2,
                "has_mechanism": False,
                "mechanism": None,
                "simulation_ready": False,
                "required_parameters": [],
                "disclaimer": settings.disclaimer,
                "not_for_direct_clinical_decision": True,
            }

        return {
            "drug1": drug1,
            "drug2": drug2,
            "has_mechanism": True,
            "mechanism": {
                "pathway": mechanism["pathway"],
                "effect": mechanism["effect"],
                "interaction_type": mechanism["interaction_type"],
                "description": mechanism["description"],
                "substrate": mechanism["substrate"],
                "perpetrator": mechanism["perpetrator"],
            },
            "simulation_ready": True,
            "required_parameters": list(mechanism["required_parameters"]),
            "disclaimer": settings.disclaimer,
            "not_for_direct_clinical_decision": True,
        }

    def simulate_pk_interaction(
        self,
        drug1: str,
        drug2: str,
        cl_total: float,
        fm: float,
        inhibitor_concentration: float,
        ki: float,
    ) -> dict[str, Any]:
        """Run a PBPK-lite simulation for supported CYP inhibition pairs."""
        explanation = self.explain_interaction_mechanism(drug1, drug2)
        if not explanation["has_mechanism"]:
            return {
                "drug1": drug1,
                "drug2": drug2,
                "has_mechanism": False,
                "simulation_status": "failed",
                "error": "No supported simulation mechanism found for this pair",
                "disclaimer": settings.disclaimer,
                "not_for_direct_clinical_decision": True,
            }

        mechanism = explanation["mechanism"]
        if mechanism["interaction_type"] != "cyp_reversible_inhibition":
            return {
                "drug1": drug1,
                "drug2": drug2,
                "has_mechanism": True,
                "mechanism": mechanism,
                "simulation_status": "failed",
                "error": "Mechanism is known but not supported by the simulator",
                "disclaimer": settings.disclaimer,
                "not_for_direct_clinical_decision": True,
            }

        simulation = self.simulation.simulate_cyp_reversible_inhibition(
            substrate=mechanism["substrate"],
            inhibitor=mechanism["perpetrator"],
            cl_total=cl_total,
            fm=fm,
            inhibitor_concentration=inhibitor_concentration,
            ki=ki,
        )
        if "error" in simulation:
            return {
                "drug1": drug1,
                "drug2": drug2,
                "has_mechanism": True,
                "mechanism": mechanism,
                "simulation_status": "failed",
                "error": simulation["error"],
                "simulation": simulation,
                "disclaimer": settings.disclaimer,
                "not_for_direct_clinical_decision": True,
            }

        return {
            "drug1": drug1,
            "drug2": drug2,
            "has_mechanism": True,
            "mechanism": mechanism,
            "simulation_status": "completed",
            "simulation": simulation,
            "disclaimer": settings.disclaimer,
            "not_for_direct_clinical_decision": True,
        }

    async def get_all_interactions(
        self,
        drug_name: str,
    ) -> dict[str, Any]:
        """
        Get all interaction information for a drug.

        Args:
            drug_name: Name of the drug

        Returns:
            Complete interaction profile
        """
        drug_normalized = self._normalize_drug_name(drug_name)
        if not drug_normalized:
            return {
                "drug_name": drug_name,
                "drug_interactions": [],
                "food_interactions": [],
                "source_label_excerpts": [],
                "error": "Drug name cannot be blank",
                **self._safety_metadata(),
            }

        cache_key = self._cache_key(f"all_interactions:{CACHE_SCHEMA_VERSION}", drug_normalized)
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # Get local drug-drug interactions from database
        local_drug_interactions = []
        for (d1, d2), interaction_data in DRUG_DRUG_INTERACTIONS.items():
            if self._drug_names_match(d1, drug_normalized) or self._drug_names_match(
                d2, drug_normalized
            ):
                other_drug = d2 if self._drug_names_match(d1, drug_normalized) else d1
                local_drug_interactions.append(
                    {
                        "interacting_drug": other_drug,
                        "severity": interaction_data.get("severity"),
                        "description": interaction_data.get("description"),
                        "management_consideration": self._management_consideration(
                            str(interaction_data.get("severity", ""))
                        ),
                        "source_recommendation_note": (
                            "Original local database guidance is intentionally "
                            "summarized as a clinical review consideration."
                        ),
                    }
                )

        # Get food interactions
        food_info = await self.check_food_drug_interaction(drug_name)

        # Get FDA label interactions
        fda_interactions = await self.fda.get_drug_interactions_from_label(drug_name)
        source_label_excerpts = []
        if fda_interactions:
            for section in ["drug_interactions", "contraindications", "warnings"]:
                source_label_excerpts.extend(
                    self._source_label_excerpt(section, text)
                    for text in fda_interactions.get(section, [])
                )

        result = {
            "drug_name": drug_name,
            "drug_interactions": local_drug_interactions,
            "food_interactions": food_info.get("food_interactions", []),
            "source_label_excerpts": source_label_excerpts,
            "note": "Drug interaction data from local database (RxNorm API discontinued 2025)",
            **self._safety_metadata(),
        }

        self.cache.set(cache_key, result)
        return result

    def _normalize_drug_name(self, drug_name: str) -> str:
        """Normalize drug names for local lookup without guessing synonyms."""
        return re.sub(r"\s+", " ", drug_name.strip().lower())

    def _drug_names_match(self, known_name: str, query_name: str) -> bool:
        """Match normalized drug names while rejecting blank and tiny substrings."""
        known_normalized = self._normalize_drug_name(known_name)
        query_normalized = self._normalize_drug_name(query_name)
        if not known_normalized or not query_normalized:
            return False
        if known_normalized == query_normalized:
            return True
        if (
            len(known_normalized) < MIN_PARTIAL_MATCH_LENGTH
            or len(query_normalized) < MIN_PARTIAL_MATCH_LENGTH
        ):
            return False
        return known_normalized in query_normalized or query_normalized in known_normalized

    def _food_interaction_view(self, interaction: dict[str, Any]) -> dict[str, Any]:
        """Return a non-prescriptive food interaction record."""
        return {
            "food": interaction.get("food"),
            "effect": interaction.get("effect"),
            "severity": interaction.get("severity"),
            "management_consideration": self._management_consideration(
                str(interaction.get("severity", ""))
            ),
            "source_recommendation_note": (
                "Original local database guidance is intentionally summarized as "
                "a clinical review consideration."
            ),
        }

    def _source_label_excerpt(self, section: str, text: str) -> dict[str, str]:
        """Return raw label text as provenance, not as a recommendation."""
        return {
            "source": "FDA label",
            "section": section,
            "text": text,
            "provenance_note": (
                "Raw labeling excerpt provided for provenance; it is not generated "
                "clinical advice."
            ),
        }

    def _management_consideration(self, severity: str) -> str:
        """Return non-prescriptive clinical review language for an interaction."""
        severity_normalized = severity.lower()
        if severity_normalized == "contraindicated":
            return (
                "Potential contraindication signal. Confirm with current labeling "
                "and a qualified clinician or pharmacist before any therapy decision."
            )
        if severity_normalized == "high":
            return (
                "High-severity interaction signal. Clinician or pharmacist review, "
                "monitoring, and evidence-based adjustment may be needed."
            )
        if severity_normalized == "moderate":
            return (
                "Moderate interaction signal. Review patient-specific risk factors, "
                "monitoring needs, and current labeling."
            )
        return (
            "Interaction signal detected. Review current evidence and patient-specific "
            "context before clinical action."
        )

    def _severity_rank(
        self,
        interaction_result: dict[str, Any],
        severity_order: dict[str, int],
    ) -> int:
        """Return a stable severity rank even for FDA-only interaction hits."""
        interactions = interaction_result.get("interactions") or []
        if not interactions:
            return 4
        severity = str(interactions[0].get("severity", "")).lower()
        return severity_order.get(severity, 4)

    def _safety_metadata(self) -> dict[str, Any]:
        """Shared safety metadata for interaction outputs."""
        return {
            "safety_note": SAFETY_NOTE,
            "disclaimer": settings.disclaimer,
            "not_for_direct_clinical_decision": True,
        }

    def _cache_key(self, *args) -> str:
        """Generate cache key from arguments."""
        key_str = ":".join(str(a) for a in args)
        return hashlib.sha256(key_str.encode()).hexdigest()
