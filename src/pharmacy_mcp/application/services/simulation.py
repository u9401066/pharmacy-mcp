"""PBPK-lite simulation service backed by trusted formulas."""

from __future__ import annotations

import math
from typing import Any

from pharmacy_mcp.config import settings
from pharmacy_mcp.domain.value_objects.formula import FormulaDefinition
from pharmacy_mcp.infrastructure.knowledge.formula_catalog import FormulaCatalog


class SimulationService:
    """Deterministic PK/DDI calculations using trusted formula definitions."""

    def __init__(self, formula_catalog: FormulaCatalog | None = None) -> None:
        self.formula_catalog = formula_catalog or FormulaCatalog()

    def simulate_concentration_time(
        self,
        dose: float,
        vd: float,
        ke: float,
        time: float,
    ) -> dict[str, Any]:
        """Estimate concentration after a bolus dose."""
        finite_error = self._finite_error(dose=dose, vd=vd, ke=ke, time=time)
        if finite_error:
            return self._error(finite_error)
        if dose < 0:
            return self._error("dose cannot be negative")
        if vd <= 0:
            return self._error("vd must be positive")
        if ke < 0:
            return self._error("ke cannot be negative")
        if time < 0:
            return self._error("time cannot be negative")

        try:
            concentration = (dose / vd) * math.exp(-ke * time)
        except (OverflowError, ZeroDivisionError) as exc:
            return self._error(f"calculation failed: {exc}")
        if not math.isfinite(concentration):
            return self._error("calculation produced a non-finite concentration")

        formula = self._require_formula("one_compartment_concentration")
        return self._result(
            formula=formula,
            inputs={"dose": dose, "vd": vd, "ke": ke, "time": time},
            outputs={"concentration": round(concentration, 4)},
        )

    def calculate_accumulation_factor(self, ke: float, tau: float) -> dict[str, Any]:
        """Estimate first-order steady-state accumulation factor."""
        finite_error = self._finite_error(ke=ke, tau=tau)
        if finite_error:
            return self._error(finite_error)
        if ke <= 0:
            return self._error("ke must be positive")
        if tau <= 0:
            return self._error("tau must be positive")

        try:
            denominator = 1 - math.exp(-ke * tau)
            if denominator <= 1e-12:
                return self._error(
                    "ke * tau is too small for a stable accumulation estimate"
                )
            accumulation_factor = 1 / denominator
        except (OverflowError, ZeroDivisionError) as exc:
            return self._error(f"calculation failed: {exc}")
        if not math.isfinite(accumulation_factor):
            return self._error("calculation produced a non-finite accumulation factor")

        formula = self._require_formula("multiple_dose_accumulation")
        return self._result(
            formula=formula,
            inputs={"ke": ke, "tau": tau},
            outputs={"accumulation_factor": round(accumulation_factor, 4)},
        )

    def adjust_renal_clearance(
        self,
        cl_nonrenal: float,
        cl_renal: float,
        renal_function_ratio: float,
    ) -> dict[str, Any]:
        """Estimate total clearance after renal function adjustment."""
        finite_error = self._finite_error(
            cl_nonrenal=cl_nonrenal,
            cl_renal=cl_renal,
            renal_function_ratio=renal_function_ratio,
        )
        if finite_error:
            return self._error(finite_error)
        if cl_nonrenal < 0:
            return self._error("cl_nonrenal cannot be negative")
        if cl_renal < 0:
            return self._error("cl_renal cannot be negative")
        if renal_function_ratio < 0:
            return self._error("renal_function_ratio cannot be negative")

        adjusted_clearance = cl_nonrenal + cl_renal * renal_function_ratio
        if not math.isfinite(adjusted_clearance):
            return self._error("calculation produced a non-finite clearance")

        formula = self._require_formula("renal_clearance_adjustment")
        return self._result(
            formula=formula,
            inputs={
                "cl_nonrenal": cl_nonrenal,
                "cl_renal": cl_renal,
                "renal_function_ratio": renal_function_ratio,
            },
            outputs={"adjusted_clearance": round(adjusted_clearance, 4)},
        )

    def simulate_cyp_reversible_inhibition(
        self,
        substrate: str,
        inhibitor: str,
        cl_total: float,
        fm: float,
        inhibitor_concentration: float,
        ki: float,
    ) -> dict[str, Any]:
        """Estimate clearance and AUC ratio for reversible CYP inhibition."""
        finite_error = self._finite_error(
            cl_total=cl_total,
            fm=fm,
            inhibitor_concentration=inhibitor_concentration,
            ki=ki,
        )
        if finite_error:
            return self._error(finite_error)
        if cl_total <= 0:
            return self._error("cl_total must be positive")
        if not 0 <= fm <= 1:
            return self._error("fm must be between 0 and 1")
        if inhibitor_concentration < 0:
            return self._error("inhibitor_concentration cannot be negative")
        if ki <= 0:
            return self._error("ki must be positive")

        try:
            inhibition_ratio = inhibitor_concentration / ki
            inhibited_clearance = cl_total * ((1 - fm) + fm / (1 + inhibition_ratio))
            if inhibited_clearance <= 1e-12:
                return self._error(
                    "inhibited clearance is too close to zero for a stable AUC ratio"
                )
            auc_ratio = cl_total / inhibited_clearance
        except (OverflowError, ZeroDivisionError) as exc:
            return self._error(f"calculation failed: {exc}")
        if not math.isfinite(inhibited_clearance) or not math.isfinite(auc_ratio):
            return self._error("calculation produced non-finite CYP inhibition outputs")

        cyp_formula = self._require_formula("cyp_reversible_inhibition_clearance")
        auc_formula = self._require_formula("auc_ratio_from_clearance")
        assumptions = tuple(
            dict.fromkeys((*cyp_formula.assumptions, *auc_formula.assumptions))
        )
        limitations = tuple(
            dict.fromkeys((*cyp_formula.limitations, *auc_formula.limitations))
        )
        references = tuple(
            dict.fromkeys((*cyp_formula.references, *auc_formula.references))
        )

        result = self._result(
            formula=cyp_formula,
            inputs={
                "cl_total": cl_total,
                "fm": fm,
                "inhibitor_concentration": inhibitor_concentration,
                "ki": ki,
            },
            outputs={
                "inhibited_clearance": round(inhibited_clearance, 4),
                "auc_ratio": round(auc_ratio, 4),
            },
            assumptions=assumptions,
            limitations=limitations,
            references=references,
        )
        result["formula_ids"] = [cyp_formula.id, auc_formula.id]
        result["output_formula_ids"] = {
            "inhibited_clearance": cyp_formula.id,
            "auc_ratio": auc_formula.id,
        }
        result["formula_expressions"] = {
            cyp_formula.id: cyp_formula.expression,
            auc_formula.id: auc_formula.expression,
        }
        result["output_units"]["auc_ratio"] = auc_formula.outputs["auc_ratio"].unit
        result["interaction_type"] = "cyp_reversible_inhibition"
        result["inputs"]["substrate"] = substrate
        result["inputs"]["inhibitor"] = inhibitor
        return result

    def calculate_auc_ratio_from_clearance(
        self,
        cl_baseline: float,
        cl_altered: float,
    ) -> dict[str, Any]:
        """Estimate AUC ratio from baseline and altered clearance."""
        finite_error = self._finite_error(
            cl_baseline=cl_baseline,
            cl_altered=cl_altered,
        )
        if finite_error:
            return self._error(finite_error)
        if cl_baseline <= 0:
            return self._error("cl_baseline must be positive")
        if cl_altered <= 0:
            return self._error("cl_altered must be positive")

        auc_ratio = cl_baseline / cl_altered
        if not math.isfinite(auc_ratio):
            return self._error("calculation produced a non-finite AUC ratio")

        formula = self._require_formula("auc_ratio_from_clearance")
        return self._result(
            formula=formula,
            inputs={"cl_baseline": cl_baseline, "cl_altered": cl_altered},
            outputs={"auc_ratio": round(auc_ratio, 4)},
        )

    def adjust_elimination_for_temperature(
        self,
        ke_ref: float,
        temperature_c: float,
        reference_c: float = 37.0,
        q10: float = 2.0,
    ) -> dict[str, Any]:
        """Estimate elimination rate after Q10 temperature correction."""
        finite_error = self._finite_error(
            ke_ref=ke_ref,
            temperature_c=temperature_c,
            reference_c=reference_c,
            q10=q10,
        )
        if finite_error:
            return self._error(finite_error)
        if ke_ref < 0:
            return self._error("ke_ref cannot be negative")
        if q10 <= 0:
            return self._error("q10 must be positive")

        try:
            adjusted_ke = ke_ref * q10 ** ((temperature_c - reference_c) / 10)
        except OverflowError as exc:
            return self._error(f"calculation failed: {exc}")
        if not math.isfinite(adjusted_ke):
            return self._error("calculation produced a non-finite elimination rate")

        formula = self._require_formula("temperature_corrected_elimination")
        return self._result(
            formula=formula,
            inputs={
                "ke_ref": ke_ref,
                "temperature_c": temperature_c,
                "reference_c": reference_c,
                "q10": q10,
            },
            outputs={"adjusted_ke": round(adjusted_ke, 6)},
        )

    def _require_formula(self, formula_id: str) -> FormulaDefinition:
        """Return a formula or raise when the catalog is inconsistent."""
        formula = self.formula_catalog.get_formula(formula_id)
        if formula is None:
            raise ValueError(f"Trusted formula missing from catalog: {formula_id}")
        return formula

    def _result(
        self,
        *,
        formula: FormulaDefinition,
        inputs: dict[str, Any],
        outputs: dict[str, float],
        assumptions: tuple[str, ...] | None = None,
        limitations: tuple[str, ...] | None = None,
        references: tuple[Any, ...] | None = None,
    ) -> dict[str, Any]:
        """Build a consistent simulation result."""
        return {
            "catalog_version": self.formula_catalog.version,
            "formula_id": formula.id,
            "formula_name": formula.name,
            "formula_expression": formula.expression,
            "inputs": inputs,
            "input_units": {
                name: parameter.unit for name, parameter in formula.parameters.items()
            },
            "outputs": outputs,
            "output_units": {
                name: output.unit for name, output in formula.outputs.items()
            },
            "assumptions": list(assumptions or formula.assumptions),
            "limitations": list(limitations or formula.limitations),
            "references": [
                reference.to_dict() if hasattr(reference, "to_dict") else reference
                for reference in (references or formula.references)
            ],
            "confidence": "screening",
            "disclaimer": settings.disclaimer,
            "not_for_direct_clinical_decision": True,
        }

    def _finite_error(self, **values: float) -> str | None:
        """Return an error when any numeric input is not finite."""
        for name, value in values.items():
            if not math.isfinite(value):
                return f"{name} must be finite"
        return None

    def _error(self, message: str) -> dict[str, Any]:
        """Build a fail-closed structured error."""
        return {
            "error": message,
            "simulation_status": "failed",
            "disclaimer": settings.disclaimer,
            "not_for_direct_clinical_decision": True,
        }
