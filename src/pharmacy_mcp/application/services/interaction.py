"""Drug interaction service."""

import hashlib
from typing import Any

from pharmacy_mcp.infrastructure.api.rxnorm import RxNormClient
from pharmacy_mcp.infrastructure.api.fda import FDAClient
from pharmacy_mcp.infrastructure.cache.disk_cache import CacheService
from pharmacy_mcp.domain.entities.interaction import (
    DrugInteraction,
    InteractionSeverity,
    InteractionType,
)


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


class InteractionService:
    """Service for checking drug-drug and food-drug interactions."""
    
    def __init__(
        self,
        rxnorm_client: RxNormClient | None = None,
        fda_client: FDAClient | None = None,
        cache: CacheService | None = None,
    ):
        self.rxnorm = rxnorm_client or RxNormClient()
        self.fda = fda_client or FDAClient()
        self.cache = cache or CacheService()
    
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
        cache_key = self._cache_key("ddi", *sorted([drug1.lower(), drug2.lower()]))
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        drug1_lower = drug1.lower()
        drug2_lower = drug2.lower()
        
        # Check local database for interactions
        interactions = []
        
        # Try to find interaction in local database
        for (d1, d2), interaction_data in DRUG_DRUG_INTERACTIONS.items():
            # Check if either drug matches (partial match allowed)
            d1_match = d1 in drug1_lower or drug1_lower in d1
            d2_match = d2 in drug2_lower or drug2_lower in d2
            d1_match_rev = d1 in drug2_lower or drug2_lower in d1
            d2_match_rev = d2 in drug1_lower or drug1_lower in d2
            
            if (d1_match and d2_match) or (d1_match_rev and d2_match_rev):
                interactions.append({
                    "description": interaction_data.get("description"),
                    "severity": interaction_data.get("severity"),
                    "recommendation": interaction_data.get("recommendation"),
                    "drugs_involved": [drug1, drug2],
                })
        
        # Also get from FDA label for additional context
        fda_interactions = await self.fda.get_drug_interactions_from_label(drug1)
        fda_mentions_drug2 = False
        fda_context = []
        
        if fda_interactions:
            for text in fda_interactions.get("drug_interactions", []):
                if drug2_lower in text.lower():
                    fda_mentions_drug2 = True
                    fda_context.append(text)
        
        result = {
            "drug1": drug1,
            "drug2": drug2,
            "interactions": interactions,
            "interaction_count": len(interactions),
            "has_interaction": len(interactions) > 0 or fda_mentions_drug2,
            "fda_mentions_interaction": fda_mentions_drug2,
            "fda_context": fda_context[:2] if fda_context else [],  # Limit to first 2
            "source": "local_database",
            "note": "RxNorm Drug Interaction API was discontinued by NLM in 2025. Using local database.",
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
            return {"drugs": drugs, "interactions": [], "error": "Need at least 2 drugs"}
        
        all_interactions = []
        checked_pairs = set()
        
        for i, drug1 in enumerate(drugs):
            for drug2 in drugs[i + 1:]:
                pair = tuple(sorted([drug1.lower(), drug2.lower()]))
                if pair in checked_pairs:
                    continue
                checked_pairs.add(pair)
                
                result = await self.check_drug_drug_interaction(drug1, drug2)
                if result.get("has_interaction"):
                    all_interactions.append(result)
        
        # Sort by severity
        severity_order = {"contraindicated": 0, "high": 1, "moderate": 2, "low": 3}
        all_interactions.sort(
            key=lambda x: severity_order.get(
                x.get("interactions", [{}])[0].get("severity", "").lower(),
                4
            )
        )
        
        return {
            "drugs": drugs,
            "interactions": all_interactions,
            "total_interactions": len(all_interactions),
            "pairs_checked": len(checked_pairs),
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
        drug_lower = drug_name.lower()
        
        # Check local database first
        local_interactions = []
        for drug_key, interactions in FOOD_DRUG_INTERACTIONS.items():
            if drug_key in drug_lower or drug_lower in drug_key:
                local_interactions.extend(interactions)
        
        # Also get from FDA label
        fda_interactions = await self.fda.get_drug_interactions_from_label(drug_name)
        
        # Extract food-related warnings from FDA label
        fda_food_info = []
        if fda_interactions:
            for section in ["drug_interactions", "precautions"]:
                content = fda_interactions.get(section, [])
                for text in content:
                    text_lower = text.lower()
                    if any(food in text_lower for food in ["food", "meal", "grapefruit", "dairy", "alcohol"]):
                        fda_food_info.append(text)
        
        return {
            "drug_name": drug_name,
            "food_interactions": local_interactions,
            "fda_food_info": fda_food_info,
            "has_food_interactions": len(local_interactions) > 0 or len(fda_food_info) > 0,
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
        cache_key = self._cache_key("all_interactions", drug_name.lower())
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        drug_lower = drug_name.lower()
        
        # Get local drug-drug interactions from database
        local_drug_interactions = []
        for (d1, d2), interaction_data in DRUG_DRUG_INTERACTIONS.items():
            if d1 in drug_lower or drug_lower in d1 or d2 in drug_lower or drug_lower in d2:
                other_drug = d2 if (d1 in drug_lower or drug_lower in d1) else d1
                local_drug_interactions.append({
                    "interacting_drug": other_drug,
                    "severity": interaction_data.get("severity"),
                    "description": interaction_data.get("description"),
                    "recommendation": interaction_data.get("recommendation"),
                })
        
        # Get food interactions
        food_info = await self.check_food_drug_interaction(drug_name)
        
        # Get FDA label interactions
        fda_interactions = await self.fda.get_drug_interactions_from_label(drug_name)
        
        result = {
            "drug_name": drug_name,
            "drug_interactions": local_drug_interactions,
            "food_interactions": food_info.get("food_interactions", []),
            "fda_drug_interactions": fda_interactions.get("drug_interactions", []) if fda_interactions else [],
            "contraindications": fda_interactions.get("contraindications", []) if fda_interactions else [],
            "warnings": fda_interactions.get("warnings", []) if fda_interactions else [],
            "note": "Drug interaction data from local database (RxNorm API discontinued 2025)",
        }
        
        self.cache.set(cache_key, result)
        return result
    
    def _cache_key(self, *args) -> str:
        """Generate cache key from arguments."""
        key_str = ":".join(str(a) for a in args)
        return hashlib.md5(key_str.encode()).hexdigest()
