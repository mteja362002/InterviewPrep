"""Assessment Recommendations — deterministic next-step suggestion.

Advisory only: suggests what the learner might do next after an assessment.
DERIVED FROM the canonical AssessmentEvidence contract (not from the raw
score), so every assessment type produces recommendations through one
uniform path. Does NOT touch the planner or roadmap ordering.
"""
from __future__ import annotations

from typing import Optional

from .difficulty import recommend_from_verdict
from .schemas import (
    AssessmentEvidence, AssessmentRecommendation, Feedback, Verdict,
)


def build_recommendation(
    evidence: AssessmentEvidence,
    feedback: Feedback,
) -> AssessmentRecommendation:
    """Derive the next-step recommendation purely from evidence signals."""
    suggested = recommend_from_verdict(
        evidence.difficulty_achieved or "medium", evidence.verdict,
    )

    # Revision/weakness signals take priority over a bare verdict so future
    # assessment types (which may not map cleanly to CORRECT/INCORRECT) still
    # produce sensible recommendations from the same canonical signals.
    if evidence.revision_trigger or evidence.weakness_confirmation:
        return AssessmentRecommendation(
            next_action="revise",
            reason=feedback.revision_recommendation or "Revisit fundamentals before reattempting.",
            suggested_difficulty=suggested,
        )
    if evidence.verdict == Verdict.CORRECT:
        return AssessmentRecommendation(
            next_action="advance",
            reason="Demonstrated mastery on this assessment.",
            suggested_difficulty=suggested,
        )
    return AssessmentRecommendation(
        next_action="reattempt",
        reason="Partially correct — refine weak areas and try again.",
        suggested_difficulty=suggested,
    )
