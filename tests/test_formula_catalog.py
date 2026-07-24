"""Tests for trusted PK/DDI formula catalog."""

import json
from pathlib import Path

import pytest

from pharmacy_mcp.application.services.simulation import SimulationService
from pharmacy_mcp.infrastructure.knowledge.formula_catalog import FormulaCatalog

EXPECTED_FORMULA_IDS = {
    "one_compartment_concentration",
    "multiple_dose_accumulation",
    "renal_clearance_adjustment",
    "cyp_reversible_inhibition_clearance",
    "auc_ratio_from_clearance",
    "temperature_corrected_elimination",
}
CATALOG_PATH = (
    Path(__file__).parent.parent
    / "src"
    / "pharmacy_mcp"
    / "data"
    / "formulas"
    / "trusted_pk_ddi.json"
)


class TestFormulaCatalog:
    """Trusted formula catalog tests."""

    def test_catalog_loads_initial_trusted_formulas(self):
        """Catalog loads the initial 0.9.0 trusted PK/DDI formulas."""
        catalog = FormulaCatalog()

        assert {
            formula.id for formula in catalog.list_formulas()
        } == EXPECTED_FORMULA_IDS
        assert catalog.count == len(EXPECTED_FORMULA_IDS)

    def test_formula_metadata_is_auditable(self):
        """Every trusted formula carries provenance and safety metadata."""
        catalog = FormulaCatalog()

        for formula in catalog.list_formulas():
            assert formula.status == "trusted"
            assert formula.expression
            assert formula.parameters
            assert formula.assumptions
            assert formula.limitations
            assert formula.references
            assert formula.validation_cases

    def test_get_unknown_formula_returns_none(self):
        """Unknown formula IDs return None instead of raising."""
        catalog = FormulaCatalog()

        assert catalog.get_formula("missing_formula") is None

    def test_formula_to_dict_preserves_parameter_units(self):
        """Formula serialization keeps parameter units for MCP resources."""
        catalog = FormulaCatalog()
        formula = catalog.get_formula("cyp_reversible_inhibition_clearance")

        assert formula is not None
        serialized = formula.to_dict()
        assert serialized["parameters"]["fm"]["unit"] == "fraction"
        assert (
            serialized["parameters"]["ki"]["unit"] == "same_as_inhibitor_concentration"
        )

    def test_catalog_validation_cases_execute_against_simulation_service(self):
        """Catalog validation cases stay synchronized with implementation keys."""
        catalog = FormulaCatalog()
        service = SimulationService(formula_catalog=catalog)
        dispatch = {
            "one_compartment_concentration": service.simulate_concentration_time,
            "multiple_dose_accumulation": service.calculate_accumulation_factor,
            "renal_clearance_adjustment": service.adjust_renal_clearance,
            "cyp_reversible_inhibition_clearance": (
                lambda **kwargs: service.simulate_cyp_reversible_inhibition(
                    substrate="validation substrate",
                    inhibitor="validation inhibitor",
                    **kwargs,
                )
            ),
            "auc_ratio_from_clearance": service.calculate_auc_ratio_from_clearance,
            "temperature_corrected_elimination": (
                service.adjust_elimination_for_temperature
            ),
        }

        for formula in catalog.list_formulas():
            assert formula.implementation_key in dispatch
            for case in formula.validation_cases:
                result = dispatch[formula.implementation_key](**case["inputs"])
                assert "error" not in result
                for output_name, expected_value in case["expected"].items():
                    assert result["outputs"][output_name] == pytest.approx(
                        expected_value,
                        abs=case["tolerance"],
                    )

    @pytest.mark.parametrize(
        ("mutator", "message"),
        [
            (
                lambda formula: formula.update({"status": "draft"}),
                "must be trusted",
            ),
            (
                lambda formula: formula.update(
                    {"implementation_key": "auc_ratio_from_clearance"}
                ),
                "implementation key must match formula id",
            ),
            (
                lambda formula: formula["validation_cases"][0]["inputs"].update(
                    {"unknown_input": 1}
                ),
                "unknown inputs",
            ),
            (
                lambda formula: formula["validation_cases"][0].update({"tolerance": 0}),
                "tolerance must be positive",
            ),
        ],
    )
    def test_catalog_rejects_untrusted_or_malformed_formulas(
        self,
        tmp_path: Path,
        mutator,
        message: str,
    ):
        """Malformed trusted formula metadata fails before runtime simulation."""
        data = _catalog_data()
        mutator(data["formulas"][0])
        path = tmp_path / "catalog.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        with pytest.raises(ValueError, match=message):
            FormulaCatalog(path)

    def test_catalog_rejects_non_standard_nan_constants(self, tmp_path: Path):
        """Trusted JSON must not use non-standard NaN or Infinity tokens."""
        path = tmp_path / "catalog.json"
        path.write_text(
            '{"version":"test","formulas":[{"id":"bad","value":NaN}]}',
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="Invalid numeric constant"):
            FormulaCatalog(path)

    def test_optional_formula_defaults_are_serialized(self):
        """Optional catalog defaults are visible to clients."""
        catalog = FormulaCatalog()
        formula = catalog.get_formula("temperature_corrected_elimination")

        assert formula is not None
        serialized = formula.to_dict()
        assert serialized["parameters"]["reference_c"]["required"] is False
        assert serialized["parameters"]["reference_c"]["default"] == 37.0
        assert serialized["parameters"]["q10"]["required"] is False
        assert serialized["parameters"]["q10"]["default"] == 2.0


def _catalog_data() -> dict:
    """Load the bundled catalog as mutable test data."""
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
