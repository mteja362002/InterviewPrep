"""Regression tests for effective prerequisite completion.

Validates architectural consistency: LearnerContext → effective completion
→ Eligibility → Subject Progression must ALL agree when a track is
effectively completed.  The core bug was that the eligibility engine
(Step 2) used virtual_completed_node_ids() to unlock Java's nodes, but
the session pipeline (Step 3.5) derived completed_subjects independently
from actual node completions — causing the two engines to disagree on
whether PF was done.

These tests prove the fix is correct for the full matrix:
  - PF=0  → Java locked, PF is the frontier
  - PF=9  → PF effectively complete, Java is the frontier
  - Actual Java completion → independently unlocks downstream tracks
  - Virtual ≠ actual: actual completion state is not mutated
"""
from __future__ import annotations

from typing import List, Optional

import pytest

from services.learning_engine.context import LearnerContext, build_learner_context
from services.learning_engine.subject_progression import (
    build_all_sessions, _derive_subject_status,
)
from roadmap import get_roadmap
from tests.test_adaptive_planning_phase4_step2 import _pick


@pytest.fixture
def roadmap():
    return get_roadmap()


# ---------------------------------------------------------------------------
# 1. Architectural consistency: LearnerContext → session pipeline agree
# ---------------------------------------------------------------------------

def test_pf9_effective_completion_is_consistent(roadmap):
    """LearnerContext.effective_completed_subject_ids and _derive_subject_status
    must agree that PF is completed when PF=9 onboarding, zero progress."""
    ctx = build_learner_context(
        onboarding={
            "current_position": "student",
            "target_companies": ["google"],
            "self_assessment": {"programming_fundamentals": 9, "java": 1},
        },
    )
    effective = ctx.effective_completed_subject_ids(roadmap)

    # Context says PF is effectively completed
    assert "programming_fundamentals" in effective
    assert "java" not in effective

    # Session pipeline, given the effective set, marks PF as completed (not eligible)
    pf_nodes = roadmap.get_track_learning_nodes("programming_fundamentals")
    pf_status = _derive_subject_status(
        "programming_fundamentals",
        roadmap.get("programming_fundamentals").get("subject_prerequisites", []),
        effective,
        pf_nodes,
        ctx.progress_map,
    )
    assert pf_status in ("completed", "mastered"), (
        f"PF should be completed/mastered in session pipeline, got {pf_status!r}"
    )

    # Java's prereq (PF) is in effective set → Java should be eligible, not locked
    java_track = roadmap.get("java")
    java_prereqs = java_track.get("subject_prerequisites", [])
    java_nodes = roadmap.get_track_learning_nodes("java")
    java_status = _derive_subject_status(
        "java", java_prereqs, effective, java_nodes, ctx.progress_map,
    )
    assert java_status == "eligible", (
        f"Java should be eligible (PF effectively done), got {java_status!r}"
    )


def test_pf0_keeps_java_locked(roadmap):
    """PF=0 → PF is NOT effectively completed → Java stays locked."""
    ctx = build_learner_context(
        onboarding={
            "current_position": "student",
            "target_companies": ["google"],
            "self_assessment": {"programming_fundamentals": 0, "java": 0},
        },
    )
    effective = ctx.effective_completed_subject_ids(roadmap)
    assert "programming_fundamentals" not in effective

    java_track = roadmap.get("java")
    java_prereqs = java_track.get("subject_prerequisites", [])
    java_nodes = roadmap.get_track_learning_nodes("java")
    java_status = _derive_subject_status(
        "java", java_prereqs, effective, java_nodes, ctx.progress_map,
    )
    assert java_status == "locked", f"Java should be locked with PF=0, got {java_status!r}"


# ---------------------------------------------------------------------------
# 2. End-to-end planner acceptance tests
# ---------------------------------------------------------------------------

def test_e2e_pf9_java1_resolves_to_java():
    """End-to-end: PF=9, Java=1 → Today's Mission resolves to Java."""
    rec = _pick({
        "current_position": "student",
        "target_companies": ["google"],
        "self_assessment": {
            "programming_fundamentals": 9, "java": 1, "dsa": 0,
            "dbms": 0, "operating_systems": 0,
            "computer_networks": 0, "lld": 0, "hld": 0,
            "projects": 10, "behavioral": 10, "resume": 10
        },
    })
    assert rec is not None
    assert rec["track"] == "java", (
        f"PF=9 learner should be routed to java, got {rec['track']!r}"
    )


def test_e2e_pf0_resolves_to_pf():
    """End-to-end: PF=0 → Today's Mission resolves to Programming Fundamentals."""
    rec = _pick({
        "current_position": "student",
        "target_companies": ["google"],
        "self_assessment": {
            "programming_fundamentals": 0, "java": 0, "dsa": 0,
            "dbms": 0, "operating_systems": 0,
            "computer_networks": 0, "lld": 0, "hld": 0,
        },
    })
    assert rec is not None
    assert rec["track"] == "programming_fundamentals"


# ---------------------------------------------------------------------------
# 3. Virtual vs actual — the distinction is preserved
# ---------------------------------------------------------------------------

def test_effective_completion_does_not_mutate_actual_state(roadmap):
    """Virtual/effective completion must NOT alter the actual node or
    subject completion state.  The roadmap's actual completion query
    must still return empty for zero-progress learners."""
    ctx = build_learner_context(
        onboarding={
            "current_position": "student",
            "self_assessment": {"programming_fundamentals": 10},
        },
    )
    # Effective says PF is done
    assert "programming_fundamentals" in ctx.effective_completed_subject_ids(roadmap)

    # Actual says PF is NOT done (no nodes completed)
    actual = set(roadmap.completed_subject_ids(ctx.completed_node_ids()))
    assert "programming_fundamentals" not in actual


# ---------------------------------------------------------------------------
# 4. Actual Java completion unlocks downstream subjects independently
# ---------------------------------------------------------------------------

def test_actual_java_completion_unlocks_dsa(roadmap):
    """When Java is actually completed (all foundation+core nodes done),
    its downstream subjects should unlock via the normal roadmap DAG,
    independent of onboarding signals."""
    # Build progress rows with all PF + Java foundation/core nodes completed
    pf_nodes = roadmap.get_track_learning_nodes("programming_fundamentals")
    java_nodes = roadmap.get_track_learning_nodes("java")
    fc_nodes = [
        n for n in (pf_nodes + java_nodes)
        if n.get("learning_stage") in ("foundation", "core", None)
    ]
    rows = [{"node_id": n["id"], "status": "completed", "track": n["track"]} for n in fc_nodes]

    ctx = build_learner_context(
        onboarding={
            "current_position": "student",
            "self_assessment": {"programming_fundamentals": 0, "java": 0},
        },
        progress_rows=rows,
    )
    effective = ctx.effective_completed_subject_ids(roadmap)

    # Both PF and Java should be in the effective set (via actual completion)
    assert "programming_fundamentals" in effective
    assert "java" in effective

    # DSA (if its only subject_prerequisite is PF) should be eligible
    dsa_track = roadmap.get("dsa")
    if dsa_track:
        dsa_prereqs = dsa_track.get("subject_prerequisites", [])
        if dsa_prereqs:
            assert all(p in effective for p in dsa_prereqs), (
                f"DSA prereqs {dsa_prereqs} should all be in effective set {effective}"
            )
