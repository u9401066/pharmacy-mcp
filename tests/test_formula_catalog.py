"""Tests for trusted PK/DDI formula catalog."""

from pharmacy_mcp.infrastructure.knowledge.formula_catalog import FormulaCatalog

EXPECTED_FORMULA_IDS = {
    "one_compartment_concentration",
    "multiple_dose_accumulation",
    "renal_clearance_adjustment",
    "cyp_reversible_inhibition_clearance",
    "auc_ratio_from_clearance",
    "temperature_corrected_elimination",
}


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
