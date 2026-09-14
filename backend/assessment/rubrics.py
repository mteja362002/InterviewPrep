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

# Sprint 3A: MCQ rubric — single dimension, deterministic binary evaluation.
_MCQ_RUBRIC: List[RubricDimension] = [
    RubricDimension(key="accuracy", label="Accuracy", weight=1.0,
                    description="Binary: correct answer selected or not."),
]

# Sprint 3A: Behavioral rubric — qualitative structure for feedback only.
# No deterministic evaluator exists; this rubric supports question generation
# and feedback structure, NOT certified evidence.
_BEHAVIORAL_RUBRIC: List[RubricDimension] = [
    RubricDimension(key="relevance", label="Relevance", weight=0.40,
                    description="Response addresses the STAR scenario directly."),
    RubricDimension(key="depth", label="Depth", weight=0.30,
                    description="Specificity and detail of examples provided."),
    RubricDimension(key="communication", label="Communication", weight=0.30,
                    description="Clarity and structure of the response."),
]

# Sprint 3A: System Design rubric — qualitative structure for feedback only.
# Covers both LLD (design) and HLD (system_design). No deterministic evaluator.
_SYSTEM_DESIGN_RUBRIC: List[RubricDimension] = [
    RubricDimension(key="requirements", label="Requirements Coverage", weight=0.30,
                    description="All functional/non-functional requirements addressed."),
    RubricDimension(key="architecture", label="Architecture Quality", weight=0.30,
                    description="Soundness of component design and interactions."),
    RubricDimension(key="trade_offs", label="Trade-off Analysis", weight=0.20,
                    description="Awareness of design trade-offs and alternatives."),
    RubricDimension(key="communication", label="Communication", weight=0.20,
                    description="Clarity and structure of the design explanation."),
]

_RUBRICS: Dict[str, List[RubricDimension]] = {
    AssessmentType.CODING.value: _CODING_RUBRIC,
    AssessmentType.MCQ.value: _MCQ_RUBRIC,
    AssessmentType.THEORY.value: _MCQ_RUBRIC,  # same evaluation as MCQ
    AssessmentType.BEHAVIORAL.value: _BEHAVIORAL_RUBRIC,
    AssessmentType.SYSTEM_DESIGN.value: _SYSTEM_DESIGN_RUBRIC,
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
