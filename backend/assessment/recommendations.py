"""Assessment Recommendations — deterministic next-step suggestion.

Advisory only: suggests what the learner might do next after an assessment.
Does NOT touch the planner or roadmap ordering.
"""
from __future__ import annotations

from typing import Optional

from .difficulty import recommend_from_verdict
from .schemas import AssessmentRecommendation, Feedback, Question, Result, Verdict


def build_recommendation(
    result: Result,
    feedback: Feedback,
    *,
    question: Optional[Question] = None,
) -> AssessmentRecommendation:
    difficulty = question.difficulty if question else "medium"
    suggested = recommend_from_verdict(difficulty, result.verdict)

    if result.verdict == Verdict.CORRECT:
        return AssessmentRecommendation(
            next_action="advance",
            reason="Demonstrated mastery on this assessment.",
            suggested_difficulty=suggested,
        )
    if result.verdict == Verdict.INCORRECT:
        return AssessmentRecommendation(
            next_action="revise",
            reason=feedback.revision_recommendation or "Revisit fundamentals before reattempting.",
            suggested_difficulty=suggested,
        )
    return AssessmentRecommendation(
        next_action="reattempt",
        reason="Partially correct — refine weak areas and try again.",
        suggested_difficulty=suggested,
    )
