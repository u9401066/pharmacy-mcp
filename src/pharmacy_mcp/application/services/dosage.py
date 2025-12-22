"""Dosage calculation service."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from pharmacy_mcp.domain.value_objects.dosage import Dosage, DosageUnit


class PatientPopulation(str, Enum):
    """Patient population types for dosing."""
    ADULT = "adult"
    PEDIATRIC = "pediatric"
    GERIATRIC = "geriatric"
    RENAL_IMPAIRMENT = "renal_impairment"
    HEPATIC_IMPAIRMENT = "hepatic_impairment"


@dataclass
class PatientParameters:
    """Patient parameters for dosage calculation."""
    weight_kg: float | None = None
    height_cm: float | None = None
    age_years: int | None = None
    gender: str | None = None
    creatinine_clearance: float | None = None  # mL/min
    population: PatientPopulation = PatientPopulation.ADULT
    
    @property
    def bsa(self) -> float | None:
        """Calculate Body Surface Area (Mosteller formula) in m²."""
        if self.weight_kg and self.height_cm:
            return ((self.height_cm * self.weight_kg) / 3600) ** 0.5
        return None
    
    @property
    def ideal_body_weight(self) -> float | None:
        """Calculate Ideal Body Weight (Devine formula) in kg."""
        if self.height_cm and self.gender:
            height_inches = self.height_cm / 2.54
            if self.gender.lower() in ["m", "male"]:
                return 50 + 2.3 * (height_inches - 60)
            else:
                return 45.5 + 2.3 * (height_inches - 60)
        return None


class DosageService:
    """Service for dosage calculations."""
    
    def calculate_weight_based_dose(
        self,
        dose_per_kg: float,
        patient_weight_kg: float,
        dose_unit: str = "mg",
        max_dose: float | None = None,
        round_to: float = 1.0,
    ) -> dict[str, Any]:
        """
        Calculate weight-based dosage.
        
        Args:
            dose_per_kg: Dose per kg of body weight
            patient_weight_kg: Patient weight in kg
            dose_unit: Unit of dose (mg, mcg, etc.)
            max_dose: Maximum dose cap
            round_to: Round dose to nearest value
            
        Returns:
            Calculated dose information
        """
        calculated_dose = dose_per_kg * patient_weight_kg
        
        if max_dose and calculated_dose > max_dose:
            final_dose = max_dose
            capped = True
        else:
            final_dose = calculated_dose
            capped = False
        
        # Round dose
        if round_to > 0:
            final_dose = round(final_dose / round_to) * round_to
        
        return {
            "dose_per_kg": dose_per_kg,
            "patient_weight_kg": patient_weight_kg,
            "calculated_dose": calculated_dose,
            "final_dose": final_dose,
            "dose_unit": dose_unit,
            "max_dose": max_dose,
            "capped": capped,
            "formula": f"{dose_per_kg} {dose_unit}/kg × {patient_weight_kg} kg = {final_dose} {dose_unit}",
        }
    
    def calculate_bsa_based_dose(
        self,
        dose_per_m2: float,
        height_cm: float,
        weight_kg: float,
        dose_unit: str = "mg",
        max_dose: float | None = None,
    ) -> dict[str, Any]:
        """
        Calculate BSA-based dosage (commonly used in oncology).
        
        Args:
            dose_per_m2: Dose per m² of body surface area
            height_cm: Patient height in cm
            weight_kg: Patient weight in kg
            dose_unit: Unit of dose
            max_dose: Maximum dose cap
            
        Returns:
            Calculated dose information
        """
        # Mosteller formula for BSA
        bsa = ((height_cm * weight_kg) / 3600) ** 0.5
        calculated_dose = dose_per_m2 * bsa
        
        if max_dose and calculated_dose > max_dose:
            final_dose = max_dose
            capped = True
        else:
            final_dose = round(calculated_dose, 2)
            capped = False
        
        return {
            "dose_per_m2": dose_per_m2,
            "bsa": round(bsa, 2),
            "calculated_dose": round(calculated_dose, 2),
            "final_dose": final_dose,
            "dose_unit": dose_unit,
            "max_dose": max_dose,
            "capped": capped,
            "formula": f"{dose_per_m2} {dose_unit}/m² × {round(bsa, 2)} m² = {final_dose} {dose_unit}",
        }
    
    def calculate_creatinine_clearance(
        self,
        age_years: int,
        weight_kg: float,
        serum_creatinine: float,
        gender: str,
    ) -> dict[str, Any]:
        """
        Calculate Creatinine Clearance (Cockcroft-Gault formula).
        
        Args:
            age_years: Patient age in years
            weight_kg: Patient weight in kg
            serum_creatinine: Serum creatinine in mg/dL
            gender: Patient gender (m/f)
            
        Returns:
            CrCl value and interpretation
        """
        if serum_creatinine <= 0:
            return {"error": "Serum creatinine must be positive"}
        
        crcl = ((140 - age_years) * weight_kg) / (72 * serum_creatinine)
        
        if gender.lower() in ["f", "female"]:
            crcl *= 0.85
        
        crcl = round(crcl, 1)
        
        # Determine renal function category
        if crcl >= 90:
            category = "Normal"
        elif crcl >= 60:
            category = "Mild impairment"
        elif crcl >= 30:
            category = "Moderate impairment"
        elif crcl >= 15:
            category = "Severe impairment"
        else:
            category = "End-stage renal disease"
        
        return {
            "creatinine_clearance": crcl,
            "unit": "mL/min",
            "category": category,
            "formula": "Cockcroft-Gault",
            "inputs": {
                "age": age_years,
                "weight_kg": weight_kg,
                "serum_creatinine_mg_dl": serum_creatinine,
                "gender": gender,
            },
        }
    
    def calculate_pediatric_dose(
        self,
        adult_dose: float,
        child_weight_kg: float,
        dose_unit: str = "mg",
        method: str = "weight",
        child_age_years: int | None = None,
        child_bsa: float | None = None,
    ) -> dict[str, Any]:
        """
        Calculate pediatric dose from adult dose.
        
        Args:
            adult_dose: Standard adult dose
            child_weight_kg: Child's weight in kg
            dose_unit: Unit of dose
            method: Calculation method (weight, age, bsa)
            child_age_years: Child's age in years (for age-based)
            child_bsa: Child's BSA in m² (for BSA-based)
            
        Returns:
            Calculated pediatric dose
        """
        standard_adult_weight = 70  # kg
        standard_adult_bsa = 1.73  # m²
        
        if method == "weight":
            # Clark's rule (weight-based)
            pediatric_dose = (child_weight_kg / standard_adult_weight) * adult_dose
            formula = f"Clark's rule: (child weight / 70 kg) × adult dose"
        
        elif method == "age" and child_age_years is not None:
            # Young's rule (age-based)
            pediatric_dose = (child_age_years / (child_age_years + 12)) * adult_dose
            formula = f"Young's rule: (age / (age + 12)) × adult dose"
        
        elif method == "bsa" and child_bsa is not None:
            # BSA-based
            pediatric_dose = (child_bsa / standard_adult_bsa) * adult_dose
            formula = f"BSA method: (child BSA / 1.73 m²) × adult dose"
        
        else:
            return {"error": f"Invalid method or missing parameters for {method}"}
        
        return {
            "adult_dose": adult_dose,
            "pediatric_dose": round(pediatric_dose, 2),
            "dose_unit": dose_unit,
            "method": method,
            "formula": formula,
            "inputs": {
                "child_weight_kg": child_weight_kg,
                "child_age_years": child_age_years,
                "child_bsa": child_bsa,
            },
        }
    
    def convert_dose_units(
        self,
        value: float,
        from_unit: str,
        to_unit: str,
    ) -> dict[str, Any]:
        """
        Convert between dose units.
        
        Args:
            value: Dose value
            from_unit: Source unit
            to_unit: Target unit
            
        Returns:
            Converted dose
        """
        # Conversion factors to mg
        to_mg = {
            "g": 1000,
            "mg": 1,
            "mcg": 0.001,
            "μg": 0.001,
            "ng": 0.000001,
        }
        
        from_unit_lower = from_unit.lower()
        to_unit_lower = to_unit.lower()
        
        if from_unit_lower not in to_mg or to_unit_lower not in to_mg:
            return {"error": f"Unsupported unit conversion: {from_unit} to {to_unit}"}
        
        # Convert to mg, then to target unit
        mg_value = value * to_mg[from_unit_lower]
        converted = mg_value / to_mg[to_unit_lower]
        
        return {
            "original_value": value,
            "original_unit": from_unit,
            "converted_value": converted,
            "converted_unit": to_unit,
        }
    
    def calculate_infusion_rate(
        self,
        total_dose: float,
        dose_unit: str,
        volume_ml: float,
        duration_hours: float,
    ) -> dict[str, Any]:
        """
        Calculate IV infusion rate.
        
        Args:
            total_dose: Total dose to infuse
            dose_unit: Unit of dose
            volume_ml: Total volume in mL
            duration_hours: Infusion duration in hours
            
        Returns:
            Infusion rate information
        """
        if duration_hours <= 0 or volume_ml <= 0:
            return {"error": "Duration and volume must be positive"}
        
        concentration = total_dose / volume_ml
        rate_ml_hr = volume_ml / duration_hours
        rate_dose_hr = total_dose / duration_hours
        
        return {
            "total_dose": total_dose,
            "dose_unit": dose_unit,
            "volume_ml": volume_ml,
            "duration_hours": duration_hours,
            "concentration": round(concentration, 4),
            "concentration_unit": f"{dose_unit}/mL",
            "rate_ml_hr": round(rate_ml_hr, 2),
            "rate_dose_hr": round(rate_dose_hr, 2),
            "rate_dose_unit": f"{dose_unit}/hr",
        }
