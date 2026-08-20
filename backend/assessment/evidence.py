"""Evidence Engine — emits structured evidence for Learner Intelligence.

Evidence is the deterministic OUTPUT of an assessment. It is EXPOSED for
Learner Intelligence to consume on its own terms; the Assessment Engine
never mutates planner state, learner metrics, confidence, or revision
schedules. This preserves the one-way flow:

    Assessment -> Evidence -> (Learner Intelligence decides) -> Planner
"""
from __future__ import annotations

from typing import Optional

from .schemas import (
    Assessment, Attempt, Evidence, Question, Result, Verdict,
)

_WEAK_SCORE = 50.0
_REPEATED_ATTEMPTS = 3


def build_evidence(
    assessment: Assessment,
    result: Result,
    *,
    attempt: Optional[Attempt] = None,
    question: Optional[Question] = None,
) -> Evidence:
    correctness = next(
        (d.score for d in result.dimension_scores if d.key == "correctness"), result.overall_score,
    )
    coding_accuracy = round(correctness / 100.0, 3)
    problem_solving = round(result.overall_score / 100.0, 3)
    completion_quality = round(
        ((result.overall_score / 100.0) + result.edge_case_coverage) / 2.0, 3,
    )

    attempts_count = 0
    if attempt is not None:
        attempts_count = int((attempt.metadata or {}).get("attempt_number", 1))
    repeated_mistakes = attempts_count >= _REPEATED_ATTEMPTS and result.verdict != Verdict.CORRECT

    weakness_confirmation = result.verdict == Verdict.INCORRECT
    revision_trigger = result.verdict != Verdict.CORRECT and result.overall_score < _WEAK_SCORE

    # Signed suggestion in [-1, 1]; LI decides how (or whether) to apply it.
    if result.verdict == Verdict.CORRECT:
        topic_confidence_delta = round(min(1.0, result.overall_score / 100.0), 3)
    elif result.verdict == Verdict.INCORRECT:
        topic_confidence_delta = round(-1.0 * (1.0 - result.overall_score / 100.0), 3)
    else:
        topic_confidence_delta = 0.0

    return Evidence(
        assessment_id=assessment.id,
        user_id=assessment.user_id,
        assessment_type=assessment.assessment_type,
        roadmap_node_id=assessment.roadmap_node_id,
        mission_id=assessment.mission_id,
        coding_accuracy=coding_accuracy,
        problem_solving=problem_solving,
        completion_quality=completion_quality,
        difficulty_achieved=(question.difficulty if question else None),
        repeated_mistakes=repeated_mistakes,
        topic_confidence_delta=topic_confidence_delta,
        weakness_confirmation=weakness_confirmation,
        revision_trigger=revision_trigger,
        verdict=result.verdict,
    )
