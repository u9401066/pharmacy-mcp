"""Trusted formula catalog."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from pharmacy_mcp.domain.value_objects.formula import FormulaDefinition

SUPPORTED_IMPLEMENTATION_KEYS = {
    "one_compartment_concentration",
    "multiple_dose_accumulation",
    "renal_clearance_adjustment",
    "cyp_reversible_inhibition_clearance",
    "auc_ratio_from_clearance",
    "temperature_corrected_elimination",
}


class FormulaCatalog:
    """Load and query trusted PK/DDI formulas."""

    def __init__(self, data_path: Path | None = None) -> None:
        if data_path is None:
            data_path = (
                Path(__file__).parent.parent.parent
                / "data"
                / "formulas"
                / "trusted_pk_ddi.json"
            )

        self.version = ""
        self.updated = ""
        self._formulas: dict[str, FormulaDefinition] = {}
        self._load_data(data_path)

    def _load_data(self, data_path: Path) -> None:
        """Load trusted formula catalog data."""
        if not data_path.exists():
            raise FileNotFoundError(f"Formula catalog file not found: {data_path}")

        with data_path.open(encoding="utf-8") as file:
            data: dict[str, Any] = json.load(
                file,
                parse_constant=_reject_json_constant,
            )

        self.version = str(data.get("version", ""))
        self.updated = str(data.get("updated", ""))
        formulas: dict[str, FormulaDefinition] = {}
        for item in data.get("formulas", []):
            formula = FormulaDefinition.from_dict(item)
            self._validate_formula(formula)
            if formula.id in formulas:
                raise ValueError(f"Duplicate formula id in catalog: {formula.id}")
            formulas[formula.id] = formula
        self._formulas = formulas

    def list_formulas(self, status: str | None = "trusted") -> list[FormulaDefinition]:
        """List formula definitions, optionally filtered by status."""
        formulas = list(self._formulas.values())
        if status is None:
            return formulas
        return [formula for formula in formulas if formula.status == status]

    def get_formula(self, formula_id: str) -> FormulaDefinition | None:
        """Return a formula definition by ID."""
        return self._formulas.get(formula_id)

    def to_dict(self, status: str | None = "trusted") -> dict[str, Any]:
        """Serialize the catalog."""
        return {
            "version": self.version,
            "updated": self.updated,
            "formula_count": len(self.list_formulas(status=status)),
            "formulas": [
                formula.to_dict() for formula in self.list_formulas(status=status)
            ],
        }

    @property
    def count(self) -> int:
        """Return formula count."""
        return len(self._formulas)

    def _validate_formula(self, formula: FormulaDefinition) -> None:
        """Validate required trusted formula metadata."""
        if formula.implementation_key not in SUPPORTED_IMPLEMENTATION_KEYS:
            raise ValueError(
                f"Unsupported formula implementation key: {formula.implementation_key}"
            )
        if formula.status != "trusted":
            raise ValueError(f"Executable formula {formula.id} must be trusted")
        if formula.id != formula.implementation_key:
            raise ValueError(
                f"Formula {formula.id} implementation key must match formula id"
            )
        missing_fields = [
            field_name
            for field_name, value in {
                "expression": formula.expression,
                "parameters": formula.parameters,
                "outputs": formula.outputs,
                "assumptions": formula.assumptions,
                "limitations": formula.limitations,
                "references": formula.references,
                "validation_cases": formula.validation_cases,
            }.items()
            if not value
        ]
        if missing_fields:
            raise ValueError(
                f"Trusted formula {formula.id} missing metadata: "
                f"{', '.join(missing_fields)}"
            )
        for reference in formula.references:
            if not (reference.url or reference.citation):
                raise ValueError(
                    f"Trusted formula {formula.id} reference lacks citation or URL"
                )
        self._validate_cases(formula)

    def _validate_cases(self, formula: FormulaDefinition) -> None:
        """Validate formula case schemas and finite numeric expectations."""
        for index, case in enumerate(formula.validation_cases):
            if not isinstance(case, dict):
                raise ValueError(
                    f"Formula {formula.id} validation case {index} invalid"
                )
            inputs = case.get("inputs")
            expected = case.get("expected")
            tolerance = case.get("tolerance")
            if not isinstance(inputs, dict) or not inputs:
                raise ValueError(
                    f"Formula {formula.id} validation case {index} missing inputs"
                )
            if not isinstance(expected, dict) or not expected:
                raise ValueError(
                    f"Formula {formula.id} validation case {index} missing expected"
                )
            unknown_inputs = set(inputs) - set(formula.parameters)
            if unknown_inputs:
                raise ValueError(
                    f"Formula {formula.id} validation case {index} has unknown "
                    f"inputs: {', '.join(sorted(unknown_inputs))}"
                )
            missing_required = {
                name
                for name, parameter in formula.parameters.items()
                if parameter.required and name not in inputs
            }
            if missing_required:
                raise ValueError(
                    f"Formula {formula.id} validation case {index} missing required "
                    f"inputs: {', '.join(sorted(missing_required))}"
                )
            unknown_outputs = set(expected) - set(formula.outputs)
            if unknown_outputs:
                raise ValueError(
                    f"Formula {formula.id} validation case {index} has unknown "
                    f"outputs: {', '.join(sorted(unknown_outputs))}"
                )
            if not isinstance(tolerance, int | float) or not math.isfinite(tolerance):
                raise ValueError(
                    f"Formula {formula.id} validation case {index} needs finite tolerance"
                )
            if tolerance <= 0:
                raise ValueError(
                    f"Formula {formula.id} validation case {index} tolerance must be positive"
                )
            self._assert_finite_numbers(formula.id, index, "inputs", inputs)
            self._assert_finite_numbers(formula.id, index, "expected", expected)

    def _assert_finite_numbers(
        self,
        formula_id: str,
        case_index: int,
        label: str,
        values: dict[str, Any],
    ) -> None:
        """Reject non-finite numeric values in trusted validation cases."""
        for name, value in values.items():
            if isinstance(value, int | float) and not math.isfinite(value):
                raise ValueError(
                    f"Formula {formula_id} validation case {case_index} {label}.{name} "
                    "must be finite"
                )


def _reject_json_constant(value: str) -> None:
    """Reject non-standard JSON constants such as NaN and Infinity."""
    raise ValueError(f"Invalid numeric constant in formula catalog: {value}")
