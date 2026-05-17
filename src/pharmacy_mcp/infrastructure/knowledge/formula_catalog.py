"""Trusted formula catalog."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pharmacy_mcp.domain.value_objects.formula import FormulaDefinition


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
            data: dict[str, Any] = json.load(file)

        self.version = str(data.get("version", ""))
        self.updated = str(data.get("updated", ""))
        self._formulas = {
            formula.id: formula
            for formula in (
                FormulaDefinition.from_dict(item) for item in data.get("formulas", [])
            )
        }

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
