"""Tests for dosage service."""

import pytest

from pharmacy_mcp.application.services.dosage import DosageService


class TestDosageService:
    """Tests for DosageService."""
    
    @pytest.fixture
    def service(self):
        """Create dosage service."""
        return DosageService()
    
    def test_calculate_weight_based_dose(self, service):
        """Test weight-based dose calculation."""
        result = service.calculate_weight_based_dose(
            dose_per_kg=10,
            patient_weight_kg=70,
            dose_unit="mg",
        )
        
        assert result["calculated_dose"] == 700
        assert result["final_dose"] == 700
        assert result["dose_unit"] == "mg"
        assert not result["capped"]
    
    def test_weight_based_dose_with_cap(self, service):
        """Test weight-based dose with maximum cap."""
        result = service.calculate_weight_based_dose(
            dose_per_kg=10,
            patient_weight_kg=100,
            dose_unit="mg",
            max_dose=500,
        )
        
        assert result["calculated_dose"] == 1000
        assert result["final_dose"] == 500
        assert result["capped"] is True
    
    def test_calculate_bsa_based_dose(self, service):
        """Test BSA-based dose calculation."""
        result = service.calculate_bsa_based_dose(
            dose_per_m2=100,
            height_cm=170,
            weight_kg=70,
            dose_unit="mg",
        )
        
        assert "bsa" in result
        assert result["bsa"] > 0
        assert result["calculated_dose"] > 0
    
    def test_calculate_creatinine_clearance_male(self, service):
        """Test CrCl calculation for male."""
        result = service.calculate_creatinine_clearance(
            age_years=60,
            weight_kg=70,
            serum_creatinine=1.0,
            gender="male",
        )
        
        assert result["creatinine_clearance"] > 0
        assert "category" in result
        assert result["formula"] == "Cockcroft-Gault"
    
    def test_calculate_creatinine_clearance_female(self, service):
        """Test CrCl calculation for female (should be 0.85x male)."""
        male_result = service.calculate_creatinine_clearance(
            age_years=60,
            weight_kg=70,
            serum_creatinine=1.0,
            gender="male",
        )
        
        female_result = service.calculate_creatinine_clearance(
            age_years=60,
            weight_kg=70,
            serum_creatinine=1.0,
            gender="female",
        )
        
        expected = male_result["creatinine_clearance"] * 0.85
        assert abs(female_result["creatinine_clearance"] - expected) < 0.5
    
    def test_calculate_pediatric_dose_weight(self, service):
        """Test pediatric dose calculation by weight."""
        result = service.calculate_pediatric_dose(
            adult_dose=500,
            child_weight_kg=25,
            method="weight",
        )
        
        assert result["pediatric_dose"] < result["adult_dose"]
        assert "formula" in result
    
    def test_calculate_pediatric_dose_age(self, service):
        """Test pediatric dose calculation by age."""
        result = service.calculate_pediatric_dose(
            adult_dose=500,
            child_weight_kg=25,
            method="age",
            child_age_years=8,
        )
        
        # Young's rule: 8 / (8 + 12) = 0.4 × 500 = 200
        assert result["pediatric_dose"] == 200
    
    def test_convert_dose_units(self, service):
        """Test dose unit conversion."""
        # 1 g = 1000 mg
        result = service.convert_dose_units(1, "g", "mg")
        assert result["converted_value"] == 1000
        
        # 500 mcg = 0.5 mg
        result = service.convert_dose_units(500, "mcg", "mg")
        assert result["converted_value"] == 0.5
    
    def test_calculate_infusion_rate(self, service):
        """Test infusion rate calculation."""
        result = service.calculate_infusion_rate(
            total_dose=1000,
            dose_unit="mg",
            volume_ml=250,
            duration_hours=2,
        )
        
        assert result["rate_ml_hr"] == 125  # 250 / 2
        assert result["rate_dose_hr"] == 500  # 1000 / 2
        assert result["concentration"] == 4  # 1000 / 250
