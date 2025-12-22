"""Drug interaction entity."""

from dataclasses import dataclass
from enum import Enum


class InteractionSeverity(str, Enum):
    """Interaction severity levels."""
    CONTRAINDICATED = "contraindicated"  # 禁忌
    SEVERE = "severe"                     # 嚴重
    MODERATE = "moderate"                 # 中等
    MINOR = "minor"                       # 輕微
    UNKNOWN = "unknown"                   # 未知


class InteractionType(str, Enum):
    """Type of interaction."""
    DRUG_DRUG = "drug-drug"
    DRUG_FOOD = "drug-food"
    DRUG_ALCOHOL = "drug-alcohol"
    DRUG_SUPPLEMENT = "drug-supplement"
    DRUG_DISEASE = "drug-disease"


@dataclass
class DrugInteraction:
    """Drug interaction entity."""
    
    drug1_rxcui: str
    drug1_name: str
    drug2_rxcui: str
    drug2_name: str
    
    severity: InteractionSeverity = InteractionSeverity.UNKNOWN
    interaction_type: InteractionType = InteractionType.DRUG_DRUG
    
    description: str = ""
    mechanism: str | None = None
    clinical_effect: str | None = None
    management: str | None = None
    
    # Evidence
    evidence_level: str | None = None
    references: list[str] | None = None
    
    # Source
    source: str = "FDA"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "drug1": {
                "rxcui": self.drug1_rxcui,
                "name": self.drug1_name,
            },
            "drug2": {
                "rxcui": self.drug2_rxcui,
                "name": self.drug2_name,
            },
            "severity": self.severity.value,
            "interaction_type": self.interaction_type.value,
            "description": self.description,
            "mechanism": self.mechanism,
            "clinical_effect": self.clinical_effect,
            "management": self.management,
            "evidence_level": self.evidence_level,
            "source": self.source,
        }
    
    @property
    def is_severe(self) -> bool:
        """Check if interaction is severe or contraindicated."""
        return self.severity in (
            InteractionSeverity.CONTRAINDICATED,
            InteractionSeverity.SEVERE,
        )
