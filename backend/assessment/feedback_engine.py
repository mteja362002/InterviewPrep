"""Feedback Engine — structured, deterministic feedback (no free-text AI).

Builds strengths / weaknesses / missing concepts / recommendations purely
from the rubric result and problem metadata already on the question.
"""
from __future__ import annotations

from typing import List, Optional

from .difficulty import recommend_from_verdict
from .schemas import Feedback, Question, Result, Verdict

_STRONG = 75.0
_WEAK = 50.0


def build_feedback(result: Result, question: Optional[Question] = None) -> Feedback:
    strengths: List[str] = []
    weaknesses: List[str] = []
    for d in result.dimension_scores:
        if d.score >= _STRONG:
            strengths.append(d.label)
        elif d.score < _WEAK:
            weaknesses.append(d.label)

    # Missing concepts: prerequisite patterns of the assessed problem, surfaced
    # only when the learner did not clearly pass (evidence they may need them).
    missing: List[str] = []
    if question and result.verdict != Verdict.CORRECT:
        missing = list((question.metadata or {}).get("prerequisite_patterns", []))

    revision_reco: Optional[str] = None
    confidence_impact = "neutral"
    if result.verdict == Verdict.CORRECT:
        confidence_impact = "positive"
    elif result.verdict == Verdict.INCORRECT:
        confidence_impact = "negative"
        pattern = question.pattern if question else None
        revision_reco = (
            f"Revise {pattern.replace('_', ' ')} fundamentals" if pattern
            else "Revise the underlying fundamentals"
        )
    elif weaknesses:
        revision_reco = f"Reinforce: {', '.join(weaknesses)}"

    return Feedback(
        strengths=strengths,
        weaknesses=weaknesses,
        missing_concepts=missing,
        revision_recommendation=revision_reco,
        difficulty_recommendation=recommend_from_verdict(
            question.difficulty if question else "medium", result.verdict,
        ),
        confidence_impact=confidence_impact,
    )
