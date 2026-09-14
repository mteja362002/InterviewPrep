"""Evaluator Registry — type-specific, deterministic evaluation dispatch.

Sprint 3A introduces per-type evaluators.  Only types with a registered
evaluator produce certified evidence; types without one complete with
qualitative feedback only (no evidence, no LI mutation).

Invariants:
  * No evaluator calls the LLM.
  * MCQ evaluation is binary: answer_index match → CORRECT / INCORRECT.
  * BEHAVIORAL and SYSTEM_DESIGN have NO evaluator in Sprint 3A —
    completion produces qualitative feedback, not certified evidence.
  * The existing coding evaluator (evaluation_engine.evaluate) is
    registered here as the canonical CODING evaluator.
"""
from __future__ import annotations

from typing import Callable, Dict, Optional

from .schemas import (
    AssessmentType, Attempt, DimensionScore, Question, Result, Rubric, Verdict,
)

# Type alias: an evaluator takes (attempt, rubric, question) → Result.
Evaluator = Callable[[Attempt, Rubric, Optional[Question]], Result]

_EVALUATORS: Dict[AssessmentType, Evaluator] = {}


def register_evaluator(assessment_type: AssessmentType, evaluator: Evaluator) -> None:
    """Register a deterministic evaluator for an assessment type."""
    _EVALUATORS[assessment_type] = evaluator


def get_evaluator(assessment_type: AssessmentType) -> Optional[Evaluator]:
    """Return the evaluator for the type, or None if no deterministic
    evaluation exists (e.g. behavioral, system_design in Sprint 3A)."""
    return _EVALUATORS.get(assessment_type)


def has_evaluator(assessment_type: AssessmentType) -> bool:
    """True if a deterministic evaluator is registered for this type."""
    return assessment_type in _EVALUATORS


# --------------------------------------------------------------------------- #
# MCQ Evaluator — deterministic, binary
# --------------------------------------------------------------------------- #

def evaluate_mcq(
    attempt: Attempt, rubric: Rubric, question: Optional[Question] = None,
) -> Result:
    """Deterministic MCQ evaluation.

    The learner's ``selected_option`` (from attempt.metadata) is compared
    against ``answer_index`` (from question.metadata).  Exact match → CORRECT
    with accuracy 1.0; mismatch → INCORRECT with accuracy 0.0.

    No partial credit.  No AI scoring.
    """
    selected = attempt.metadata.get("selected_option")
    answer_index = (question.metadata or {}).get("answer_index") if question else None

    if selected is not None and answer_index is not None and int(selected) == int(answer_index):
        verdict = Verdict.CORRECT
        accuracy_score = 100.0
    else:
        verdict = Verdict.INCORRECT
        accuracy_score = 0.0

    dimension_scores = [
        DimensionScore(
            key="accuracy",
            label="Accuracy",
            score=accuracy_score,
            weight=1.0,
            detail="Binary MCQ evaluation: correct or incorrect.",
        ),
    ]

    return Result(
        verdict=verdict,
        overall_score=accuracy_score,
        dimension_scores=dimension_scores,
        completion_status="completed",
    )


# --------------------------------------------------------------------------- #
# Registration — coding evaluator is imported and registered at module load
# --------------------------------------------------------------------------- #

# Register MCQ evaluator (also used for THEORY — identical evaluation).
register_evaluator(AssessmentType.MCQ, evaluate_mcq)
register_evaluator(AssessmentType.THEORY, evaluate_mcq)

# Register existing coding evaluator.
from .evaluation_engine import evaluate as _coding_evaluate  # noqa: E402

register_evaluator(AssessmentType.CODING, _coding_evaluate)

# BEHAVIORAL and SYSTEM_DESIGN intentionally have NO evaluator registered.
# get_evaluator() returns None → no certified evidence, no LI mutation.
