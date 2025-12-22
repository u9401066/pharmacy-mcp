"""Drug entity and related models."""

from dataclasses import dataclass, field
from enum import Enum


class DrugType(str, Enum):
    """Drug type classification."""
    BRAND = "brand"
    GENERIC = "generic"
    INGREDIENT = "ingredient"


@dataclass
class DrugConcept:
    """RxNorm drug concept."""
    
    rxcui: str
    name: str
    synonym: str | None = None
    tty: str | None = None  # Term type
    
    def __str__(self) -> str:
        return f"{self.name} (RxCUI: {self.rxcui})"


@dataclass
class Drug:
    """Drug entity with full information."""
    
    rxcui: str
    name: str
    drug_type: DrugType = DrugType.GENERIC
    
    # Classification
    atc_codes: list[str] = field(default_factory=list)
    drug_classes: list[str] = field(default_factory=list)
    
    # Clinical info
    indications: list[str] = field(default_factory=list)
    contraindications: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    # Dosage forms
    dosage_forms: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    routes: list[str] = field(default_factory=list)
    
    # Manufacturer
    manufacturer: str | None = None
    ndc_codes: list[str] = field(default_factory=list)
    
    # Source tracking
    source: str = "RxNorm"
    last_updated: str | None = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "rxcui": self.rxcui,
            "name": self.name,
            "drug_type": self.drug_type.value,
            "atc_codes": self.atc_codes,
            "drug_classes": self.drug_classes,
            "indications": self.indications,
            "contraindications": self.contraindications,
            "warnings": self.warnings,
            "dosage_forms": self.dosage_forms,
            "strengths": self.strengths,
            "routes": self.routes,
            "manufacturer": self.manufacturer,
            "ndc_codes": self.ndc_codes,
            "source": self.source,
            "last_updated": self.last_updated,
        }
