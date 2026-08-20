"""Learner Intelligence Engine (Phase 2C).

A deterministic, first-class runtime component that models HOW a learner
learns and exposes it as an additive planner input — without any AI, ML,
prediction models, or randomness, and without new MongoDB collections.

Layout mirrors the single-responsibility philosophy of the learning engine:

    metrics.py         -- pure helpers + canonical label vocabulary
    trend_analysis.py  -- deterministic split-mean trend detection
    context.py         -- LearnerIntelligenceInput (raw signal bundle)
    velocity.py        -- (1) learning velocity
    retention.py       -- (2) retention quality
    confidence.py      -- (3) confidence trend
    weakness.py        -- (4) weakness stability (per track)
    consistency.py     -- (5) learning consistency
    revision_health.py -- (6) revision health
    coding.py          -- (7) coding growth
    mastery_trend.py   -- (8) topic mastery trend (per track)
    difficulty.py      -- (9) difficulty adaptation
    readiness.py       -- (10) interview readiness trend
    snapshot.py        -- aggregate snapshot (compute-once view)
    engine.py          -- COMPUTATION pipeline (build snapshot)
    planner_adapter.py -- CONSUMPTION pipeline (bounded scoring nudge)
    explainability.py  -- reasons derived from the same signals
"""
from .context import (
    LearnerIntelligenceInput, build_learner_intelligence_input,
)
from .engine import build_learner_intelligence, build_snapshot
from .explainability import summarize_contributions, summarize_snapshot
from .planner_adapter import learner_intelligence_signal
from .snapshot import LearnerIntelligenceSnapshot, empty_snapshot

__all__ = [
    "LearnerIntelligenceInput",
    "build_learner_intelligence_input",
    "build_learner_intelligence",
    "build_snapshot",
    "LearnerIntelligenceSnapshot",
    "empty_snapshot",
    "learner_intelligence_signal",
    "summarize_contributions",
    "summarize_snapshot",
]
