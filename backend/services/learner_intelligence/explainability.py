"""Explainability for Learner Intelligence.

Every reason emitted here is derived straight from the precomputed snapshot
(or the per-node contributions the planner adapter produced) — never a
hardcoded sentence — so the explanation can NEVER contradict the signal that
actually influenced the score. This mirrors
:mod:`company_intelligence.explainability` and feeds the same Recommendation
Insight the planner already surfaces (Mission Control, AI Mentor).
"""
from __future__ import annotations

from typing import List, Optional

from .metrics import (
    DIFFICULTY_DECREASE, DIFFICULTY_INCREASE, MASTERY_PLATEAU,
    MASTERY_REGRESSING, NEGATIVE_TRENDS, POSITIVE_TRENDS, WEAKNESS_PERSISTENT,
    WEAKNESS_RECURRING,
)
from .snapshot import LearnerIntelligenceSnapshot

_CONFIDENCE_HIGH = 7.0
_CONFIDENCE_LOW = 4.0


def _confidence_band(avg: float) -> str:
    if avg >= _CONFIDENCE_HIGH:
        return "High"
    if avg >= _CONFIDENCE_LOW:
        return "Medium"
    return "Low"


def summarize_contributions(contributions: List[dict]) -> dict:
    """Turn per-node adapter contributions into a compact, ordered summary.

    Reasons are ordered by absolute impact so the strongest driver is first
    — matching the 'Reason' list in the brief's explainability example.
    """
    if not contributions:
        return {"reasons": [], "score": 0.0, "contributions": []}

    ordered = sorted(contributions, key=lambda c: abs(c.get("value", 0.0)), reverse=True)
    reasons: List[str] = []
    for c in ordered:
        term = c.get("term")
        detail = c.get("detail", "")
        if term == "weakness_stability":
            reasons.append(f"{detail.capitalize()} weakness on this topic")
        elif term == "mastery_trend":
            reasons.append(f"Mastery {detail} on this topic")
        elif term == "difficulty_adaptation":
            action = detail.split("/")[0]
            reasons.append(f"Difficulty {action} for this learner")
        elif term == "velocity_overload":
            reasons.append("Eased off a hard task while velocity is slowing")
    score = round(sum(c.get("value", 0.0) for c in contributions), 3)
    return {"reasons": reasons, "score": score, "contributions": ordered}


def summarize_snapshot(
    snapshot: LearnerIntelligenceSnapshot,
    *,
    node: Optional[dict] = None,
) -> dict:
    """Produce the learner-level explainability block for a mission.

    Shape intentionally matches the brief's example (Reason list, Difficulty,
    Confidence). Returns an inert block (available=False) for an empty
    snapshot so callers can render nothing without special-casing.
    """
    if snapshot is None or snapshot.is_empty:
        return {"available": False, "reasons": []}

    reasons: List[str] = []

    # Weak-topic reason (track-specific when a node is provided).
    if node is not None:
        weak_state = snapshot.weakness_state(node.get("track"))
        if weak_state in (WEAKNESS_PERSISTENT, WEAKNESS_RECURRING):
            reasons.append("Weak topic")
        mastery_state = snapshot.mastery_state(node.get("track"))
        if mastery_state == MASTERY_REGRESSING:
            reasons.append("Topic mastery regressing")
        elif mastery_state == MASTERY_PLATEAU:
            reasons.append("Topic mastery plateaued")

    if snapshot.revision_health.debt_level in ("high", "moderate"):
        reasons.append("High revision debt")
    if snapshot.velocity.trend in NEGATIVE_TRENDS:
        reasons.append("Learning velocity slowing")
    elif snapshot.velocity.trend in POSITIVE_TRENDS:
        reasons.append("Learning velocity rising")
    if snapshot.consistency.trend in POSITIVE_TRENDS:
        reasons.append("Consistency improving")
    elif snapshot.consistency.trend in NEGATIVE_TRENDS:
        reasons.append("Consistency slipping")

    action = snapshot.difficulty_adaptation.action
    if action == DIFFICULTY_DECREASE:
        difficulty_label = "Difficulty decreased"
    elif action == DIFFICULTY_INCREASE:
        difficulty_label = "Difficulty increased"
    else:
        difficulty_label = "Difficulty maintained"
    reasons.append(difficulty_label)

    return {
        "available": True,
        "reasons": reasons,
        "difficulty": difficulty_label,
        "difficulty_action": action,
        "confidence": _confidence_band(snapshot.confidence_trend.current_avg),
        "confidence_trend": snapshot.confidence_trend.direction,
        "readiness_trajectory": snapshot.readiness_trend.trajectory,
        "readiness_score": snapshot.readiness_trend.score,
    }
