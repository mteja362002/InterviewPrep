"""Regression tests: planner recommendation must agree with ranking engine.

These tests verify that `get_today_learning_node()` selects the same track
as the deterministic ranking engine (`score_candidate`) would produce for
the same eligible candidates.  This guards against regressions where a
pipeline stage (e.g. session selection) inadvertently bypasses or overrides
the ranking engine's preference ordering.

Sprint: Planner → Ranking Integration Fix
"""
from __future__ import annotations

import asyncio
from typing import List, Optional

import pytest

from services.learning_engine.context import build_learner_context
from services.learning_engine.planner import get_today_learning_node
from services.learning_engine.priority_engine import score_candidate
from services.learning_engine.subject_progression import (
    build_all_sessions,
    build_daily_learning_plan,
)
from roadmap import get_roadmap


# ---------------------------------------------------------------------------
# Test doubles (identical to test_adaptive_planning_phase4_step2.py)
# ---------------------------------------------------------------------------

class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows
    async def to_list(self, length=None):
        return list(self._rows)

class _FakeCollection:
    def __init__(self, rows):
        self._rows = rows
    def find(self, query=None, projection=None):
        return _FakeCursor(list(self._rows))

class FakeDB:
    def __init__(self, rows):
        self.knowledge_nodes = _FakeCollection(rows)


@pytest.fixture
def roadmap():
    return get_roadmap()


# ---------------------------------------------------------------------------
# 1. Planner pick == ranking engine top candidate for session-pipeline path
# ---------------------------------------------------------------------------

def test_planner_pick_equals_ranking_winner_for_eligible_candidates(roadmap):
    """The planner's final recommendation must match the highest-scored
    candidate from the ranking engine, given the same learner context and
    eligible candidate set.

    This test constructs a learner state where multiple tracks are newly
    eligible, scores all session-pipeline candidates through the ranking
    engine, and verifies the planner agrees with the ranking winner."""
    onboarding = {
        "current_position": "1-3",
        "self_assessment": {
            "programming_fundamentals": 10, "java": 10,
            "dsa": 3, "dbms": 4, "operating_systems": 6,
            "computer_networks": 6, "lld": 4, "hld": 4,
        },
    }

    for company in ("google", "oracle"):
        # 1. Build the same context the planner would build
        ctx = build_learner_context(
            onboarding=onboarding,
            target_companies=[company],
        )

        # 2. Run the session pipeline to get eligible candidates
        effective = ctx.effective_completed_subject_ids(roadmap)
        sessions = build_all_sessions(
            roadmap, ctx.progress_map,
            effective_completed_subjects=effective,
        )
        plan = build_daily_learning_plan(
            sessions, roadmap, recent_track_ids=[],
        )

        # 3. Score all task plan candidates through the ranking engine
        scored = []
        for tp in plan.task_plans:
            node = roadmap.get(tp.node_id)
            if node is not None:
                p = score_candidate(node, ctx)
                scored.append((tp.session.track_id, p.score, tp.node_id))

        assert scored, f"No scored candidates for {company}"

        # 4. The ranking winner is the highest-scored candidate
        ranking_winner_track = max(scored, key=lambda x: x[1])[0]

        # 5. Run the planner
        pick = asyncio.run(get_today_learning_node(
            "user-regression",
            db=FakeDB([]),
            onboarding=onboarding,
            target_companies=[company],
        ))

        assert pick is not None, f"Planner returned None for {company}"
        assert pick["track"] == ranking_winner_track, (
            f"[{company}] Planner picked {pick['track']!r} but ranking "
            f"engine's top candidate was {ranking_winner_track!r}. "
            f"Scored: {scored}"
        )


# ---------------------------------------------------------------------------
# 2. Roadmap dictionary order does NOT override ranking
# ---------------------------------------------------------------------------

def test_roadmap_order_does_not_override_ranking(roadmap):
    """DSA appears before DBMS in roadmap dictionary order. With a learner
    state where DBMS scores higher than DSA (lower self-assessment = bigger
    gap = higher score), the planner must still pick DBMS — proving that
    roadmap ordering does not override the ranking engine."""
    onboarding = {
        "current_position": "1-3",
        "self_assessment": {
            "programming_fundamentals": 10, "java": 10,
            "dsa": 5, "dbms": 2, "operating_systems": 2,
            "computer_networks": 2, "lld": 4, "hld": 4,
        },
    }

    pick = asyncio.run(get_today_learning_node(
        "user-order-test",
        db=FakeDB([]),
        onboarding=onboarding,
        target_companies=["oracle"],
    ))

    assert pick is not None
    # DSA appears first in roadmap order. If the planner respected ranking,
    # DBMS should win because it has a much bigger knowledge gap (80% vs 50%).
    assert pick["track"] == "dbms", (
        f"Expected planner to pick 'dbms' (bigger gap) over 'dsa' "
        f"(roadmap-first), got {pick['track']!r}"
    )


# ---------------------------------------------------------------------------
# 3. Company signal produces different picks for same learner
# ---------------------------------------------------------------------------

def test_company_signal_differentiates_planner_picks(roadmap):
    """With balanced knowledge gaps, Google and Oracle must select different
    primary tracks. This proves the company signal flows through the full
    planner pipeline (not just the ranking engine in isolation)."""
    onboarding = {
        "current_position": "1-3",
        "self_assessment": {
            "programming_fundamentals": 10, "java": 10,
            "dsa": 3, "dbms": 4, "operating_systems": 6,
            "computer_networks": 6, "lld": 4, "hld": 4,
        },
    }

    google_pick = asyncio.run(get_today_learning_node(
        "user-company-test",
        db=FakeDB([]),
        onboarding=onboarding,
        target_companies=["google"],
    ))
    oracle_pick = asyncio.run(get_today_learning_node(
        "user-company-test",
        db=FakeDB([]),
        onboarding=onboarding,
        target_companies=["oracle"],
    ))

    assert google_pick is not None and oracle_pick is not None
    assert google_pick["track"] != oracle_pick["track"], (
        f"Google and Oracle both picked {google_pick['track']!r}; "
        f"company weighting should differentiate them."
    )
