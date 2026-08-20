"""Adaptive learning engine — Phase 4 orchestrator + engines.

Every layer is a single-responsibility module:

    context.py         -- LearnerContext (bundle of learner signals)
    eligibility.py     -- what is legally allowed today
    candidates.py      -- narrow to a compact candidate set
    priority_engine.py -- generalized scoring + continuity tie-break
    ranking.py         -- canonical scoring formula (used by priority_engine)
    composition.py     -- mission composition + validator + continuity
    companion.py       -- support + core (companion) recommendations
    cold_start.py      -- entry-track strategy for first-time learners
    foresight.py       -- likely-next preview + readiness estimate
    insight.py         -- explainable "why this?" payload
    pacing.py          -- interview-deadline urgency
    revision.py        -- spaced-repetition selection
    roi.py             -- roadmap-graph ROI signal
    stage_engine.py    -- subject-level learning-state derivation
    unlock.py          -- prerequisite unlock rules
    builder.py         -- recommendation DTO builder
    planner.py         -- thin orchestrator (Phase 4)
"""

from .adaptive_weights import (
    DEFAULT_ADAPTIVE_WEIGHTS, ResolvedWeights, resolve_weights,
)
from .builder import build_learning_recommendation
from .company_context import (
    CompanyContext, CompanyProfileContext, build_company_context,
)
from .context import LearnerContext, build_learner_context
from .planner import get_today_learning_node
from .priority_engine import (
    PriorityScore, rank_by_priority, score_candidate,
    score_candidates, top_candidate,
)
from .ranking import rank_learning_nodes
from .revision import (
    get_due_revision_nodes,
    get_highest_priority_revision,
    has_due_revision,
)
from .unlock import get_unlocked_nodes, is_node_unlocked, next_unlockable_nodes

__all__ = [
    "build_learning_recommendation",
    "DEFAULT_ADAPTIVE_WEIGHTS",
    "ResolvedWeights",
    "resolve_weights",
    "LearnerContext",
    "build_learner_context",
    "CompanyContext",
    "CompanyProfileContext",
    "build_company_context",
    "get_today_learning_node",
    "PriorityScore",
    "rank_by_priority",
    "score_candidate",
    "score_candidates",
    "top_candidate",
    "rank_learning_nodes",
    "get_due_revision_nodes",
    "get_highest_priority_revision",
    "has_due_revision",
    "get_unlocked_nodes",
    "is_node_unlocked",
    "next_unlockable_nodes",
]
