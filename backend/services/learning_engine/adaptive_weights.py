"""Adaptive scoring weights — the ONE tunable surface for the Priority Engine.

Purpose (Phase 4 Step 2):
    Every signal the Priority Engine consumes is a weighted term inside
    ``ranking.score_learning_node``. That formula is deliberately kept
    as one function so an explanation trace can enumerate every term.
    But every term needs a WEIGHT — and tuning weights (or adding new
    signals) should never require reading the ranking formula.

    This module centralises those weights so:

      * Product tuning happens in ONE file.
      * New signals are added by defining a new weight here and a new
        term in ``ranking.score_learning_node`` — the planner and every
        downstream consumer stay untouched.
      * Tests can override individual weights without monkey-patching
        the ranking module.

Design contract:
    * Every weight is a plain float.
    * Every weight is documented with a one-line intent describing what
      the signal REWARDS (positive) or DISCOURAGES (negative).
    * NO learner-specific / company-specific / experience-specific
      constants live here. Position enums, company ids, and track ids
      are read from data, not hardcoded weights.
    * Callers may pass an ``overrides`` dict to ``resolve_weights`` to
      shift any subset of weights for a single call — useful for
      tests and for future A/B experiments without touching the code
      path.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional


# ---------------------------------------------------------------------------
# Default weights
# ---------------------------------------------------------------------------

# NOTE: the numerical values below match the pre-Phase-4-Step-2 constants
# already used inside ranking.py so backward compatibility is preserved
# byte-for-byte when the new adaptive signals are inactive.
DEFAULT_ADAPTIVE_WEIGHTS: dict = {
    # Legacy signals (weights preserved for compatibility).
    # ---------------------------------------------------------------
    # `knowledge_gap`: the core "how far is the learner from mastering
    #  this node right now" term. Scaled by roadmap `mastery_weight`.
    "knowledge_gap": 1.0,
    #  Company relevance. Multiplied by roadmap.company_importance()
    #  aggregated across the learner's target companies.
    "company_score": 3.0,
    #  ROI (how many downstream topics this node unlocks).
    "roi_score": 0.05,
    #  Difficulty penalty (harder nodes cost more time / less throughput).
    "difficulty_penalty": 10.0,
    #  Small time-in-minutes penalty; nodes that dominate a day get less
    #  attractive than shorter, quicker wins.
    "estimated_minutes": 0.01,
    #  Sequence gate: earlier-authored siblings must finish before later
    #  siblings can be picked over them.
    "sequence_penalty": 1000.0,
    #  Recency: recently offered nodes are lightly deferred.
    "recency_penalty": 12.0,
    #  Skip deferral: nodes the learner explicitly skipped rest for a bit.
    "skip_penalty": 28.0,
    #  Same-track fatigue: mid+ learners benefit from variety.
    "fatigue_penalty": 8.0,
    #  Foundation-first: low-self-assessment learners get nudged toward
    #  roadmap-declared foundation nodes on this track.
    "foundation_bonus": 22.0,

    # ---- Phase 4 Step 2 additions --------------------------------------
    # `effective_knowledge_gap`: same shape as knowledge_gap but computed
    #  over blended (self-assessment + actual mastery) evidence. Activated
    #  when a LearnerContext is supplied; the classic term is scaled down
    #  proportionally so the total gap contribution stays bounded.
    "effective_knowledge_gap": 0.6,
    # `subject_readiness_bonus`: preference for candidates whose track has
    #  genuine learning headroom (low effective_knowledge). Kept small so
    #  it never overrides a strong node-level signal.
    "subject_readiness_bonus": 12.0,
    # `subject_transition_bonus`: nudges cross-track exploration once the
    #  learner's current track is mostly complete — supports Case B (PF
    #  complete -> Core CS / DSA), Case C (Core CS transition), Case D2
    #  (senior with weak Core CS). Weight is large so freshly-unlocked
    #  subjects genuinely dominate stale, deeper-in-track picks — but
    #  never large enough to overwhelm interview_frequency / company
    #  signals on well-known tracks.
    "subject_transition_bonus": 100.0,
    # `prerequisite_gap_penalty`: strongly penalises candidates in tracks
    #  whose prerequisites are weak in effective_knowledge. Prevents the
    #  planner from jumping into HLD/LLD when a subject-prerequisite is
    #  still lightly known. The signal is the SUM of shortfalls across
    #  every prerequisite (so a 5-prereq track like HLD accumulates much
    #  more penalty than a 1-prereq track like DSA); weight is per-unit-
    #  shortfall.
    "prerequisite_gap_penalty": 60.0,
    # `momentum_bonus`: rewards a candidate on a track where the learner
    #  is currently completing nodes at a healthy pace. Bounded so a hot
    #  streak on one track cannot completely block variety.
    "momentum_bonus": 6.0,
    # `topic_freshness_penalty`: applied when a candidate's TOPIC (not
    #  just node id) was just practised in the last mission. Prevents
    #  same-topic repetition even when the node id differs.
    "topic_freshness_penalty": 10.0,
    # `difficulty_smoothness_penalty`: penalises candidates whose authored
    #  difficulty is more than one step above the learner's current
    #  effective mastery on the track. Enforces "no jumping to advanced"
    #  without any hardcoded difficulty ladder.
    "difficulty_smoothness_penalty": 14.0,
    # `revision_confidence_bonus`: extra weight for revision-due nodes
    #  where the learner's confidence has dropped since completion —
    #  spaced-repetition + confidence signal combined.
    "revision_confidence_bonus": 20.0,

    # ---- Phase 2B · Company Intelligence -------------------------------
    # `company_intelligence_score`: bounded ADDITIVE nudge from compiled
    #  Company Intelligence (subject importance x evidence confidence x
    #  experience-level factor x priority bias). Active ONLY when a
    #  LearnerContext has company_intelligence_enabled=True AND a non-empty
    #  company_context; otherwise the term is 0.0 and the planner falls back
    #  to the roadmap-only `company_score`. Deliberately small so Company
    #  Intelligence INFLUENCES but never DOMINATES learner intelligence
    #  (compare knowledge_gap up to ~100 and subject_transition_bonus 100).
    "company_intelligence_score": 6.0,
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ResolvedWeights:
    """A frozen weight bundle used inside one scoring call."""
    weights: Mapping[str, float]

    def __getitem__(self, key: str) -> float:
        try:
            return float(self.weights[key])
        except (KeyError, TypeError, ValueError):
            return 0.0

    def get(self, key: str, default: float = 0.0) -> float:
        try:
            return float(self.weights.get(key, default))
        except (TypeError, ValueError):
            return default


def resolve_weights(overrides: Optional[Mapping[str, float]] = None) -> ResolvedWeights:
    """Return a frozen weight bundle for one scoring call.

    Callers pass ``overrides`` when they want to shift a subset of weights
    for a single call — e.g. tests that want to isolate one signal, or
    future A/B experiments. Without overrides this returns the canonical
    ``DEFAULT_ADAPTIVE_WEIGHTS`` snapshot.
    """
    merged = dict(DEFAULT_ADAPTIVE_WEIGHTS)
    if overrides:
        for k, v in overrides.items():
            try:
                merged[k] = float(v)
            except (TypeError, ValueError):
                continue
    return ResolvedWeights(weights=merged)
