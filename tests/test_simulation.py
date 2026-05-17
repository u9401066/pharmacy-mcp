"""Tests for PBPK-lite simulation service."""

import pytest

from pharmacy_mcp.application.services.simulation import SimulationService
from pharmacy_mcp.config import settings


class TestSimulationService:
    """Formula-backed simulation service tests."""

    @pytest.fixture
    def service(self) -> SimulationService:
        """Create a simulation service."""
        return SimulationService()

    def test_one_compartment_concentration(self, service: SimulationService):
        """One-compartment concentration follows the trusted validation case."""
        result = service.simulate_concentration_time(
            dose=500,
            vd=50,
            ke=0.1,
            time=6,
        )

        assert result["formula_id"] == "one_compartment_concentration"
        assert result["outputs"]["concentration"] == pytest.approx(5.49, abs=0.01)
        assert settings.disclaimer in result["disclaimer"]
        assert result["not_for_direct_clinical_decision"] is True

    def test_multiple_dose_accumulation(self, service: SimulationService):
        """Accumulation factor is calculated for first-order repeated dosing."""
        result = service.calculate_accumulation_factor(ke=0.1, tau=12)

        assert result["formula_id"] == "multiple_dose_accumulation"
        assert result["outputs"]["accumulation_factor"] == pytest.approx(1.43, abs=0.01)

    def test_renal_clearance_adjustment(self, service: SimulationService):
        """Renal clearance adjustment partitions renal and nonrenal clearance."""
        result = service.adjust_renal_clearance(
            cl_nonrenal=2,
            cl_renal=8,
            renal_function_ratio=0.25,
        )

        assert result["formula_id"] == "renal_clearance_adjustment"
        assert result["outputs"]["adjusted_clearance"] == pytest.approx(4.0)

    def test_cyp_inhibition_and_auc_ratio(self, service: SimulationService):
        """CYP reversible inhibition feeds an estimated AUC ratio."""
        result = service.simulate_cyp_reversible_inhibition(
            substrate="example substrate",
            inhibitor="example inhibitor",
            cl_total=10,
            fm=0.8,
            inhibitor_concentration=2,
            ki=1,
        )

        assert result["interaction_type"] == "cyp_reversible_inhibition"
        assert result["outputs"]["inhibited_clearance"] == pytest.approx(4.67, abs=0.01)
        assert result["outputs"]["auc_ratio"] == pytest.approx(2.14, abs=0.01)
        assert result["inputs"]["substrate"] == "example substrate"
        assert result["inputs"]["inhibitor"] == "example inhibitor"

    def test_temperature_corrected_elimination(self, service: SimulationService):
        """Temperature correction uses Q10 relationship."""
        result = service.adjust_elimination_for_temperature(
            ke_ref=0.1,
            temperature_c=39,
            reference_c=37,
            q10=2,
        )

        assert result["formula_id"] == "temperature_corrected_elimination"
        assert result["outputs"]["adjusted_ke"] == pytest.approx(0.1149, abs=0.0001)

    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({"dose": 500, "vd": 0, "ke": 0.1, "time": 6}, "vd must be positive"),
            ({"dose": 500, "vd": 50, "ke": -0.1, "time": 6}, "ke cannot be negative"),
            ({"dose": 500, "vd": 50, "ke": 0.1, "time": -1}, "time cannot be negative"),
        ],
    )
    def test_concentration_validation_errors(
        self,
        service: SimulationService,
        kwargs: dict[str, float],
        message: str,
    ):
        """Invalid PK inputs fail closed with structured errors."""
        result = service.simulate_concentration_time(**kwargs)

        assert result["error"] == message
        assert result["not_for_direct_clinical_decision"] is True

    def test_cyp_inhibition_validation_errors(self, service: SimulationService):
        """Invalid CYP DDI parameters fail closed."""
        result = service.simulate_cyp_reversible_inhibition(
            substrate="substrate",
            inhibitor="inhibitor",
            cl_total=10,
            fm=1.2,
            inhibitor_concentration=2,
            ki=1,
        )

        assert result["error"] == "fm must be between 0 and 1"
