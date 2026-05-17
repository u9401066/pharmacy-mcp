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
        assert result["catalog_version"] == "0.9.0"
        assert result["input_units"]["vd"] == "L"
        assert result["output_units"]["concentration"] == "mg/L"
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
        assert result["output_formula_ids"] == {
            "inhibited_clearance": "cyp_reversible_inhibition_clearance",
            "auc_ratio": "auc_ratio_from_clearance",
        }
        assert result["formula_expressions"]["auc_ratio_from_clearance"] == (
            "AUC_ratio = CL_baseline / CL_altered"
        )
        assert result["output_units"]["auc_ratio"] == "ratio"
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

    def test_auc_ratio_from_clearance(self, service: SimulationService):
        """AUC ratio can be validated as its own trusted formula."""
        result = service.calculate_auc_ratio_from_clearance(
            cl_baseline=10,
            cl_altered=4.67,
        )

        assert result["formula_id"] == "auc_ratio_from_clearance"
        assert result["outputs"]["auc_ratio"] == pytest.approx(2.14, abs=0.01)

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

    @pytest.mark.parametrize(
        ("method_name", "args", "message"),
        [
            (
                "simulate_concentration_time",
                {"dose": float("nan"), "vd": 50, "ke": 0.1, "time": 6},
                "dose must be finite",
            ),
            (
                "simulate_concentration_time",
                {"dose": 500, "vd": float("inf"), "ke": 0.1, "time": 6},
                "vd must be finite",
            ),
            (
                "simulate_cyp_reversible_inhibition",
                {
                    "substrate": "substrate",
                    "inhibitor": "inhibitor",
                    "cl_total": 10,
                    "fm": 1,
                    "inhibitor_concentration": float("inf"),
                    "ki": 1,
                },
                "inhibitor_concentration must be finite",
            ),
            (
                "calculate_accumulation_factor",
                {"ke": 1e-20, "tau": 1},
                "ke * tau is too small for a stable accumulation estimate",
            ),
        ],
    )
    def test_non_finite_and_unstable_inputs_fail_closed(
        self,
        service: SimulationService,
        method_name: str,
        args: dict[str, float | str],
        message: str,
    ):
        """Non-finite or numerically unstable inputs never produce success outputs."""
        result = getattr(service, method_name)(**args)

        assert result["simulation_status"] == "failed"
        assert result["error"] == message
        assert "outputs" not in result

    @pytest.mark.parametrize(
        ("method_name", "args", "message"),
        [
            (
                "simulate_concentration_time",
                {"dose": -1, "vd": 50, "ke": 0.1, "time": 6},
                "dose cannot be negative",
            ),
            (
                "calculate_accumulation_factor",
                {"ke": 0, "tau": 12},
                "ke must be positive",
            ),
            (
                "calculate_accumulation_factor",
                {"ke": 0.1, "tau": 0},
                "tau must be positive",
            ),
            (
                "adjust_renal_clearance",
                {"cl_nonrenal": -1, "cl_renal": 8, "renal_function_ratio": 0.25},
                "cl_nonrenal cannot be negative",
            ),
            (
                "adjust_renal_clearance",
                {"cl_nonrenal": 2, "cl_renal": -1, "renal_function_ratio": 0.25},
                "cl_renal cannot be negative",
            ),
            (
                "adjust_renal_clearance",
                {"cl_nonrenal": 2, "cl_renal": 8, "renal_function_ratio": -0.1},
                "renal_function_ratio cannot be negative",
            ),
            (
                "calculate_auc_ratio_from_clearance",
                {"cl_baseline": 0, "cl_altered": 4.67},
                "cl_baseline must be positive",
            ),
            (
                "calculate_auc_ratio_from_clearance",
                {"cl_baseline": 10, "cl_altered": 0},
                "cl_altered must be positive",
            ),
            (
                "adjust_elimination_for_temperature",
                {"ke_ref": -0.1, "temperature_c": 39, "reference_c": 37, "q10": 2},
                "ke_ref cannot be negative",
            ),
            (
                "adjust_elimination_for_temperature",
                {"ke_ref": 0.1, "temperature_c": 39, "reference_c": 37, "q10": 0},
                "q10 must be positive",
            ),
        ],
    )
    def test_formula_guardrails_fail_closed(
        self,
        service: SimulationService,
        method_name: str,
        args: dict[str, float],
        message: str,
    ):
        """Every formula implementation returns the same structured error shape."""
        result = getattr(service, method_name)(**args)

        assert result["simulation_status"] == "failed"
        assert result["error"] == message
        assert result["not_for_direct_clinical_decision"] is True

    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            (
                {
                    "substrate": "substrate",
                    "inhibitor": "inhibitor",
                    "cl_total": 0,
                    "fm": 0.8,
                    "inhibitor_concentration": 2,
                    "ki": 1,
                },
                "cl_total must be positive",
            ),
            (
                {
                    "substrate": "substrate",
                    "inhibitor": "inhibitor",
                    "cl_total": 10,
                    "fm": 0.8,
                    "inhibitor_concentration": -1,
                    "ki": 1,
                },
                "inhibitor_concentration cannot be negative",
            ),
            (
                {
                    "substrate": "substrate",
                    "inhibitor": "inhibitor",
                    "cl_total": 10,
                    "fm": 0.8,
                    "inhibitor_concentration": 2,
                    "ki": 0,
                },
                "ki must be positive",
            ),
            (
                {
                    "substrate": "substrate",
                    "inhibitor": "inhibitor",
                    "cl_total": 10,
                    "fm": 1,
                    "inhibitor_concentration": 1e308,
                    "ki": 1e-308,
                },
                "inhibited clearance is too close to zero for a stable AUC ratio",
            ),
        ],
    )
    def test_cyp_guardrails_fail_closed(
        self,
        service: SimulationService,
        kwargs: dict[str, float | str],
        message: str,
    ):
        """CYP simulation rejects invalid or unstable DDI parameters."""
        result = service.simulate_cyp_reversible_inhibition(**kwargs)

        assert result["simulation_status"] == "failed"
        assert result["error"] == message
