"""Trusted formula value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FormulaParameter:
    """Formula parameter metadata."""

    name: str
    unit: str
    description: str
    required: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FormulaParameter:
        """Create a parameter from catalog data."""
        return cls(
            name=str(data["name"]),
            unit=str(data["unit"]),
            description=str(data.get("description", "")),
            required=bool(data.get("required", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize parameter metadata."""
        return {
            "name": self.name,
            "unit": self.unit,
            "description": self.description,
            "required": self.required,
        }


@dataclass(frozen=True)
class FormulaReference:
    """Formula provenance reference."""

    label: str
    type: str
    url: str | None = None
    citation: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FormulaReference:
        """Create a reference from catalog data."""
        return cls(
            label=str(data["label"]),
            type=str(data.get("type", "reference")),
            url=data.get("url"),
            citation=data.get("citation"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize reference metadata."""
        return {
            "label": self.label,
            "type": self.type,
            "url": self.url,
            "citation": self.citation,
        }


@dataclass(frozen=True)
class FormulaDefinition:
    """Trusted formula definition loaded from the catalog."""

    id: str
    name: str
    version: str
    status: str
    implementation_key: str
    expression: str
    summary: str
    parameters: dict[str, FormulaParameter]
    outputs: dict[str, FormulaParameter]
    assumptions: tuple[str, ...] = field(default_factory=tuple)
    limitations: tuple[str, ...] = field(default_factory=tuple)
    references: tuple[FormulaReference, ...] = field(default_factory=tuple)
    validation_cases: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FormulaDefinition:
        """Create a formula definition from catalog data."""
        parameters = {
            item["name"]: FormulaParameter.from_dict(item)
            for item in data.get("parameters", [])
        }
        outputs = {
            item["name"]: FormulaParameter.from_dict(item)
            for item in data.get("outputs", [])
        }
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            version=str(data.get("version", "1.0.0")),
            status=str(data.get("status", "draft")),
            implementation_key=str(data["implementation_key"]),
            expression=str(data["expression"]),
            summary=str(data.get("summary", "")),
            parameters=parameters,
            outputs=outputs,
            assumptions=tuple(str(item) for item in data.get("assumptions", [])),
            limitations=tuple(str(item) for item in data.get("limitations", [])),
            references=tuple(
                FormulaReference.from_dict(item) for item in data.get("references", [])
            ),
            validation_cases=tuple(data.get("validation_cases", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize formula metadata for MCP structured responses."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "status": self.status,
            "implementation_key": self.implementation_key,
            "expression": self.expression,
            "summary": self.summary,
            "parameters": {
                name: parameter.to_dict() for name, parameter in self.parameters.items()
            },
            "outputs": {
                name: output.to_dict() for name, output in self.outputs.items()
            },
            "assumptions": list(self.assumptions),
            "limitations": list(self.limitations),
            "references": [reference.to_dict() for reference in self.references],
            "validation_cases": list(self.validation_cases),
        }


@dataclass(frozen=True)
class FormulaEvaluationResult:
    """Structured result from a formula-backed calculation."""

    formula_id: str
    inputs: dict[str, float]
    outputs: dict[str, float]
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]
    references: tuple[FormulaReference, ...]
    disclaimer: str
    confidence: str = "screening"

    def to_dict(self) -> dict[str, Any]:
        """Serialize evaluation result."""
        return {
            "formula_id": self.formula_id,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "assumptions": list(self.assumptions),
            "limitations": list(self.limitations),
            "references": [reference.to_dict() for reference in self.references],
            "confidence": self.confidence,
            "disclaimer": self.disclaimer,
            "not_for_direct_clinical_decision": True,
        }
