"""Dosage value object."""

from dataclasses import dataclass
from enum import Enum


class DosageUnit(str, Enum):
    """Dosage units."""
    MG = "mg"
    MCG = "mcg"
    G = "g"
    ML = "mL"
    UNITS = "units"
    MEQ = "mEq"
    
    # Per body weight
    MG_KG = "mg/kg"
    MCG_KG = "mcg/kg"
    
    # Per body surface area
    MG_M2 = "mg/m²"


class DosageFrequency(str, Enum):
    """Dosage frequency."""
    ONCE_DAILY = "once daily"
    TWICE_DAILY = "twice daily"
    THREE_TIMES_DAILY = "three times daily"
    FOUR_TIMES_DAILY = "four times daily"
    EVERY_6_HOURS = "every 6 hours"
    EVERY_8_HOURS = "every 8 hours"
    EVERY_12_HOURS = "every 12 hours"
    AS_NEEDED = "as needed"
    ONCE_WEEKLY = "once weekly"


@dataclass(frozen=True)
class Dosage:
    """Immutable dosage value object."""
    
    value: float
    unit: DosageUnit
    frequency: DosageFrequency | None = None
    max_daily_dose: float | None = None
    min_dose: float | None = None
    max_dose: float | None = None
    
    def __str__(self) -> str:
        """String representation."""
        result = f"{self.value} {self.unit.value}"
        if self.frequency:
            result += f" {self.frequency.value}"
        return result
    
    def to_mg(self) -> float:
        """Convert to mg if possible."""
        if self.unit == DosageUnit.MG:
            return self.value
        elif self.unit == DosageUnit.G:
            return self.value * 1000
        elif self.unit == DosageUnit.MCG:
            return self.value / 1000
        else:
            raise ValueError(f"Cannot convert {self.unit} to mg")
    
    def is_within_range(self, dose: float) -> bool:
        """Check if dose is within acceptable range."""
        if self.min_dose and dose < self.min_dose:
            return False
        if self.max_dose and dose > self.max_dose:
            return False
        return True
