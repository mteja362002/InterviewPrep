"""Assessment type registry — the extensibility seam.

Each assessment type maps to a generator callable. Sprint 3A implements:
CODING (canonical problem_bank), MCQ, THEORY, BEHAVIORAL, SYSTEM_DESIGN.
Types without a registered generator raise ``AssessmentTypeNotSupported``.
"""
from __future__ import annotations

from typing import Callable, Dict

from .schemas import AssessmentType


class AssessmentTypeNotSupported(Exception):
    """Raised when an assessment type has no generator implementation yet."""


# Types the platform knows about (all future types included by design).
SUPPORTED_TYPES = [t for t in AssessmentType]

# Sprint 3A: implemented assessment types.
IMPLEMENTED_TYPES = {
    AssessmentType.CODING,
    AssessmentType.MCQ,
    AssessmentType.THEORY,
    AssessmentType.BEHAVIORAL,
    AssessmentType.SYSTEM_DESIGN,
}

_GENERATORS: Dict[AssessmentType, Callable] = {}


def register_generator(assessment_type: AssessmentType, generator: Callable) -> None:
    _GENERATORS[assessment_type] = generator


def get_generator(assessment_type: AssessmentType) -> Callable:
    gen = _GENERATORS.get(assessment_type)
    if gen is None:
        raise AssessmentTypeNotSupported(
            f"Assessment type '{getattr(assessment_type, 'value', assessment_type)}' "
            f"is architecturally supported but not implemented in this phase."
        )
    return gen


def is_implemented(assessment_type: AssessmentType) -> bool:
    return assessment_type in IMPLEMENTED_TYPES
