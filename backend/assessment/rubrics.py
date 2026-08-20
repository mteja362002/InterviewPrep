"""Rubric Engine — reusable, weighted, configurable rubrics.

Rubrics are data, not code: a rubric is a list of weighted dimensions. The
coding rubric is defined here; the same structure is reused for every future
assessment type without redesign. Weights are configurable and validated to
sum to ~1.0.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .schemas import AssessmentType, Rubric, RubricDimension

# key -> (label, default weight, description)
_CODING_RUBRIC: List[RubricDimension] = [
    RubricDimension(key="correctness", label="Correctness", weight=0.40,
                    description="Fraction of tests passed."),
    RubricDimension(key="complexity", label="Complexity", weight=0.20,
                    description="Claimed time complexity vs expected optimum."),
    RubricDimension(key="edge_cases", label="Edge Cases", weight=0.20,
                    description="Fraction of edge cases handled."),
    RubricDimension(key="communication", label="Communication", weight=0.10,
                    description="Clarity of the submitted explanation."),
    RubricDimension(key="code_quality", label="Code Quality", weight=0.10,
                    description="Structural quality heuristics of the code."),
]

_RUBRICS: Dict[str, List[RubricDimension]] = {
    AssessmentType.CODING.value: _CODING_RUBRIC,
}


def get_rubric(
    assessment_type: AssessmentType,
    *,
    weight_overrides: Optional[Dict[str, float]] = None,
) -> Rubric:
    """Return the rubric for ``assessment_type`` with optional weight overrides.

    Overrides are re-normalized so the dimensions always sum to 1.0, keeping
    the weighted score deterministic and bounded.
    """
    key = assessment_type.value if isinstance(assessment_type, AssessmentType) else str(assessment_type)
    base = _RUBRICS.get(key)
    if not base:
        raise ValueError(f"No rubric registered for assessment type: {key}")

    dims = [d.model_copy(deep=True) for d in base]
    if weight_overrides:
        for d in dims:
            if d.key in weight_overrides:
                d.weight = float(weight_overrides[d.key])

    total = sum(d.weight for d in dims) or 1.0
    for d in dims:
        d.weight = round(d.weight / total, 6)

    return Rubric(rubric_id=f"{key}_v1", assessment_type=AssessmentType(key), dimensions=dims)


def register_rubric(assessment_type: str, dimensions: List[RubricDimension]) -> None:
    """Extension point: register a rubric for a future assessment type."""
    _RUBRICS[assessment_type] = list(dimensions)
