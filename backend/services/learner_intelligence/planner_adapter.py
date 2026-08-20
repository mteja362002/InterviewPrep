"""Learner Intelligence — the CONSUMPTION pipeline (planner adapter).

This is the ONLY place that turns a precomputed
:class:`LearnerIntelligenceSnapshot` into a bounded, additive scoring nudge
for a single candidate node. Keeping it here — and NOT inside planner.py or
ranking.py — is the decoupling the Phase 2C brief mandates: the ranking
formula simply multiplies the number this function returns by one weight.

Contract (mirrors company_intelligence.scoring):
    * PURE + DETERMINISTIC. Same snapshot + node => same (score, reasons).
    * BOUNDED. The raw signal is clamped to ``[-MAX_SIGNAL, +MAX_SIGNAL]`` so
      Learner Intelligence INFLUENCES but never DOMINATES the learner's core
      knowledge_gap term (which can reach ~100). 'The learner remains highest
      priority' — this signal refines WHICH learner-relevant node wins, it
      does not out-shout the fundamentals.
    * NEVER RAISES. Any problem returns (0.0, []) so the planner falls back.

What it rewards / penalises for a candidate on track ``T``:
    + persistent / recurring weakness on T   (the learner needs T)
    + regressing / plateau mastery on T       (T is slipping / stalled)
    - mastered mastery on T                    (gently de-emphasise)
    +/- difficulty adaptation vs node difficulty (struggling -> ease off
        hard nodes; progressing -> allow harder nodes)
    - hard node when overall velocity is declining (avoid overload)
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from .metrics import (
    DIFFICULTY_DECREASE, DIFFICULTY_INCREASE, MASTERY_MASTERED,
    MASTERY_PLATEAU, MASTERY_REGRESSING, NEGATIVE_TRENDS, WEAKNESS_PERSISTENT,
    WEAKNESS_RECOVERED, WEAKNESS_RECURRING, WEAKNESS_TEMPORARY, clamp,
)
from .snapshot import LearnerIntelligenceSnapshot

# Overall bound on the raw Learner Intelligence signal (pre-weight). Chosen so
# that, after multiplication by the adaptive weight, the contribution sits in
# the same order of magnitude as the Company Intelligence term — an influence,
# never a dominator.
MAX_SIGNAL = 3.0

# Per-term sub-weights (transparent constants, tuned so no single term can
# alone saturate MAX_SIGNAL).
_WEAKNESS_WEIGHT = {
    WEAKNESS_PERSISTENT: 1.0,
    WEAKNESS_RECURRING: 0.8,
    WEAKNESS_TEMPORARY: 0.3,
    WEAKNESS_RECOVERED: -0.2,
}
_MASTERY_WEIGHT = {
    MASTERY_REGRESSING: 0.9,
    MASTERY_PLATEAU: 0.5,
    MASTERY_MASTERED: -0.6,
}
_DIFFICULTY_DECREASE_NODE = {"hard": -1.0, "medium": -0.3, "easy": 0.3}
_DIFFICULTY_INCREASE_NODE = {"hard": 0.6, "medium": 0.1, "easy": -0.4}
_VELOCITY_OVERLOAD_PENALTY = -0.4  # hard node while velocity is declining


def learner_intelligence_signal(
    snapshot: LearnerIntelligenceSnapshot,
    node: dict,
    *,
    position: Optional[str] = None,
) -> Tuple[float, List[dict]]:
    """Return ``(bounded_score, contributions)`` for one candidate node.

    ``contributions`` is a list of ``{term, value, detail}`` dicts feeding
    the explainability layer. Returns ``(0.0, [])`` for an empty snapshot or
    a node without a track — the planner then relies on its other signals.
    """
    if snapshot is None or snapshot.is_empty or not isinstance(node, dict):
        return 0.0, []

    track = node.get("track")
    difficulty = (node.get("difficulty") or "medium").lower()
    contributions: List[dict] = []
    raw = 0.0

    # ---- Weakness stability on this track ------------------------------- #
    weak_state = snapshot.weakness_state(track)
    if weak_state and weak_state in _WEAKNESS_WEIGHT:
        val = _WEAKNESS_WEIGHT[weak_state]
        raw += val
        contributions.append({"term": "weakness_stability", "value": val, "detail": weak_state})

    # ---- Mastery trend on this track ------------------------------------ #
    mastery_state = snapshot.mastery_state(track)
    if mastery_state and mastery_state in _MASTERY_WEIGHT:
        val = _MASTERY_WEIGHT[mastery_state]
        raw += val
        contributions.append({"term": "mastery_trend", "value": val, "detail": mastery_state})

    # ---- Difficulty adaptation vs this node's difficulty ---------------- #
    action = snapshot.difficulty_adaptation.action
    if action == DIFFICULTY_DECREASE:
        val = _DIFFICULTY_DECREASE_NODE.get(difficulty, 0.0)
        if val:
            raw += val
            contributions.append({"term": "difficulty_adaptation", "value": val, "detail": f"decrease/{difficulty}"})
    elif action == DIFFICULTY_INCREASE:
        val = _DIFFICULTY_INCREASE_NODE.get(difficulty, 0.0)
        if val:
            raw += val
            contributions.append({"term": "difficulty_adaptation", "value": val, "detail": f"increase/{difficulty}"})

    # ---- Velocity overload guard ---------------------------------------- #
    if difficulty == "hard" and snapshot.velocity.trend in NEGATIVE_TRENDS:
        raw += _VELOCITY_OVERLOAD_PENALTY
        contributions.append({
            "term": "velocity_overload", "value": _VELOCITY_OVERLOAD_PENALTY,
            "detail": snapshot.velocity.trend,
        })

    return clamp(raw, -MAX_SIGNAL, MAX_SIGNAL), contributions
