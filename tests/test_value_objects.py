"""Tests for value objects."""

import pytest

from pharmacy_mcp.domain.value_objects.dosage import Dosage, DosageUnit, DosageFrequency
from pharmacy_mcp.domain.value_objects.severity import Severity, SeverityLevel


class TestDosage:
    """Tests for Dosage value object."""
    
    def test_create_dosage(self):
        """Test creating a dosage."""
        dosage = Dosage(
            value=500.0,
            unit=DosageUnit.MG,
            frequency=DosageFrequency.TWICE_DAILY,
        )
        
        assert dosage.value == 500.0
        assert dosage.unit == DosageUnit.MG
        assert dosage.frequency == DosageFrequency.TWICE_DAILY
    
    def test_max_daily_dose(self):
        """Test max daily dose attribute."""
        dosage = Dosage(
            value=500.0,
            unit=DosageUnit.MG,
            frequency=DosageFrequency.THREE_TIMES_DAILY,
            max_daily_dose=2000.0,
        )
        
        assert dosage.max_daily_dose == 2000.0
    
    def test_convert_to_mg(self):
        """Test conversion to mg."""
        dosage_g = Dosage(value=1.0, unit=DosageUnit.G)
        assert dosage_g.to_mg() == 1000.0
        
        dosage_mcg = Dosage(value=500.0, unit=DosageUnit.MCG)
        assert dosage_mcg.to_mg() == 0.5
    
    def test_dosage_immutability(self):
        """Test that dosage is immutable."""
        dosage = Dosage(value=500.0, unit=DosageUnit.MG)
        
        with pytest.raises(AttributeError):
            dosage.value = 1000.0


class TestSeverity:
    """Tests for Severity value object."""
    
    def test_create_severity(self):
        """Test creating a severity."""
        severity = Severity(
            level=SeverityLevel.SEVERE,
            description="High risk",
        )
        
        assert severity.level == SeverityLevel.SEVERE
        assert severity.description == "High risk"
    
    def test_severity_comparison(self):
        """Test severity level comparison."""
        contraindicated = SeverityLevel.CONTRAINDICATED
        severe = SeverityLevel.SEVERE
        minor = SeverityLevel.MINOR
        
        assert contraindicated > severe
        assert severe > minor
    
    def test_severity_color_code(self):
        """Test severity color code."""
        severity = Severity(level=SeverityLevel.CONTRAINDICATED)
        assert severity.color_code == "🔴"
        
        severity_minor = Severity(level=SeverityLevel.MINOR)
        assert severity_minor.color_code == "🟢"
    
    def test_severity_from_string(self):
        """Test creating severity from string."""
        severity = Severity.from_string("severe")
        assert severity.level == SeverityLevel.SEVERE
        
        severity = Severity.from_string("moderate")
        assert severity.level == SeverityLevel.MODERATE
