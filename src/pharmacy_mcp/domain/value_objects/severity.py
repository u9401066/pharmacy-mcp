"""Severity value object."""

from dataclasses import dataclass
from enum import IntEnum


class SeverityLevel(IntEnum):
    """Severity level with numeric ordering."""
    UNKNOWN = 0
    MINOR = 1
    MODERATE = 2
    SEVERE = 3
    CONTRAINDICATED = 4


@dataclass(frozen=True)
class Severity:
    """Severity value object."""
    
    level: SeverityLevel
    description: str = ""
    
    @classmethod
    def from_string(cls, value: str) -> "Severity":
        """Create Severity from string."""
        mapping = {
            "contraindicated": SeverityLevel.CONTRAINDICATED,
            "severe": SeverityLevel.SEVERE,
            "major": SeverityLevel.SEVERE,
            "moderate": SeverityLevel.MODERATE,
            "minor": SeverityLevel.MINOR,
            "low": SeverityLevel.MINOR,
        }
        level = mapping.get(value.lower(), SeverityLevel.UNKNOWN)
        return cls(level=level, description=value)
    
    @property
    def is_critical(self) -> bool:
        """Check if severity is critical."""
        return self.level >= SeverityLevel.SEVERE
    
    @property
    def color_code(self) -> str:
        """Get color code for display."""
        colors = {
            SeverityLevel.CONTRAINDICATED: "🔴",  # Red
            SeverityLevel.SEVERE: "🟠",           # Orange
            SeverityLevel.MODERATE: "🟡",         # Yellow
            SeverityLevel.MINOR: "🟢",            # Green
            SeverityLevel.UNKNOWN: "⚪",          # White
        }
        return colors.get(self.level, "⚪")
    
    def __str__(self) -> str:
        return f"{self.color_code} {self.level.name}"
