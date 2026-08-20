"""Learner Intelligence Engine — the COMPUTATION pipeline.

This module is the single entry point that turns raw learner signals
(:class:`LearnerIntelligenceInput`) into a precomputed
:class:`LearnerIntelligenceSnapshot`. It is deliberately separated from the
CONSUMPTION pipeline (:mod:`planner_adapter`) so future features — Analytics,
AI Mentor personalization, Mock Interviews, Predictive Analytics — can reuse
the exact same snapshot without duplicating the metric math.

Guarantees:
    * DETERMINISTIC — same input, same snapshot, always. No AI, no ML, no
      randomness, no prediction models.
    * DEFENSIVE — never raises. Any internal error degrades to the empty
      snapshot so the planner falls back cleanly (backward compatibility).
    * CHEAP — all signals are O(n) over the rows the planner already holds,
      so it can run in-memory per mission without a cache. A caching /
      event-recompute hook is provided (``build_snapshot`` accepts a
      precomputed snapshot) for when persistence is warranted in Phase 3.
"""
from __future__ import annotations

from typing import Optional

from .coding import compute_coding_growth
from .confidence import compute_confidence_trend
from .consistency import compute_consistency
from .context import LearnerIntelligenceInput, build_learner_intelligence_input
from .difficulty import compute_difficulty_adaptation
from .mastery_trend import compute_mastery_trends
from .readiness import compute_readiness_trend
from .retention import compute_retention
from .revision_health import compute_revision_health
from .snapshot import LearnerIntelligenceSnapshot, empty_snapshot
from .velocity import compute_velocity
from .weakness import compute_weakness_stability


def build_learner_intelligence(inp: LearnerIntelligenceInput) -> LearnerIntelligenceSnapshot:
    """Run the full computation pipeline over one learner's input.

    Returns an empty snapshot when there is no usable signal or if any
    computation fails — the planner then falls back to its pre-2C behaviour.
    """
    if inp is None or not inp.has_any_signal():
        return empty_snapshot()

    try:
        velocity = compute_velocity(inp)
        confidence = compute_confidence_trend(inp)
        retention = compute_retention(inp)
        consistency = compute_consistency(inp)
        revision_health = compute_revision_health(inp)
        weakness = compute_weakness_stability(inp)
        mastery = compute_mastery_trends(inp)
        coding = compute_coding_growth(inp)
        difficulty = compute_difficulty_adaptation(velocity, confidence, retention)
        readiness = compute_readiness_trend(velocity, confidence, retention, consistency)
    except Exception:  # pragma: no cover - defensive; must never break planner
        return empty_snapshot()

    return LearnerIntelligenceSnapshot(
        velocity=velocity,
        retention=retention,
        confidence_trend=confidence,
        consistency=consistency,
        revision_health=revision_health,
        weakness_stability=weakness,
        mastery_trends=mastery,
        coding_growth=coding,
        difficulty_adaptation=difficulty,
        readiness_trend=readiness,
        empty=False,
    )


def build_snapshot(
    *,
    progress_rows=None,
    recent_completions=None,
    completed_dates=None,
    recent_track_ids=None,
    skipped_node_ids=None,
    position: Optional[str] = None,
    precomputed: Optional[LearnerIntelligenceSnapshot] = None,
) -> LearnerIntelligenceSnapshot:
    """Convenience wrapper used by the planner / analytics.

    When ``precomputed`` is supplied it is returned as-is — this is the
    event-driven cache hook the Phase 2C brief describes: a caller that has
    already recomputed the snapshot after a mission completion / coding
    submission / revision event can inject it and skip recomputation. Never
    raises.
    """
    if precomputed is not None:
        return precomputed
    try:
        inp = build_learner_intelligence_input(
            progress_rows=progress_rows,
            recent_completions=recent_completions,
            completed_dates=completed_dates,
            recent_track_ids=recent_track_ids,
            skipped_node_ids=skipped_node_ids,
            position=position,
        )
        return build_learner_intelligence(inp)
    except Exception:  # pragma: no cover - defensive
        return empty_snapshot()
