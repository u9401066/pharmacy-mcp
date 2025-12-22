"""Tests for domain entities."""

import pytest

from pharmacy_mcp.domain.entities.drug import Drug, DrugConcept, DrugType
from pharmacy_mcp.domain.entities.interaction import (
    DrugInteraction,
    InteractionSeverity,
    InteractionType,
)


class TestDrugEntity:
    """Tests for Drug entity."""
    
    def test_create_drug(self):
        """Test creating a drug entity."""
        drug = Drug(
            rxcui="12345",
            name="Aspirin",
            drug_type=DrugType.GENERIC,
        )
        
        assert drug.rxcui == "12345"
        assert drug.name == "Aspirin"
        assert drug.drug_type == DrugType.GENERIC
        assert drug.drug_classes == []
        assert drug.atc_codes == []
    
    def test_drug_with_classes(self):
        """Test drug with drug classes."""
        drug = Drug(
            rxcui="12345",
            name="Aspirin",
            drug_type=DrugType.GENERIC,
            drug_classes=["NSAID", "Analgesic"],
        )
        
        assert "NSAID" in drug.drug_classes
        assert len(drug.drug_classes) == 2


class TestDrugConcept:
    """Tests for DrugConcept."""
    
    def test_create_concept(self):
        """Test creating a drug concept."""
        concept = DrugConcept(
            rxcui="12345",
            name="Aspirin 325 MG Oral Tablet",
            synonym="ASA",
            tty="SCD",
        )
        
        assert concept.rxcui == "12345"
        assert concept.name == "Aspirin 325 MG Oral Tablet"
        assert concept.synonym == "ASA"
        assert concept.tty == "SCD"


class TestDrugInteraction:
    """Tests for DrugInteraction entity."""
    
    def test_create_interaction(self):
        """Test creating a drug interaction."""
        interaction = DrugInteraction(
            drug1_rxcui="12345",
            drug1_name="Warfarin",
            drug2_rxcui="67890",
            drug2_name="Aspirin",
            severity=InteractionSeverity.SEVERE,
            description="Increased bleeding risk",
        )
        
        assert interaction.drug1_name == "Warfarin"
        assert interaction.drug2_name == "Aspirin"
        assert interaction.severity == InteractionSeverity.SEVERE
    
    def test_interaction_severity_ordering(self):
        """Test interaction severity ordering."""
        # InteractionSeverity uses string values, use IntEnum SeverityLevel for ordering
        from pharmacy_mcp.domain.value_objects.severity import SeverityLevel
        assert SeverityLevel.CONTRAINDICATED > SeverityLevel.SEVERE
        assert SeverityLevel.SEVERE > SeverityLevel.MODERATE
        assert SeverityLevel.MODERATE > SeverityLevel.MINOR
