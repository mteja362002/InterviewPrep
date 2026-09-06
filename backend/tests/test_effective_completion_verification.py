"""Semantic-verification regression tests for effective prerequisite completion.

Sprint 1 hardening: validates boundary conditions, the full subject-DAG,
and confirms that eligibility and subject progression consume the same
effective-completion concept.  Deterministic unit tests only — no MongoDB.
"""
from __future__ import annotations

import pytest

from services.learning_engine.context import (
    LearnerContext,
    build_learner_context,
    EFFECTIVE_SUBJECT_COMPLETE_THRESHOLD,
)
from services.learning_engine.subject_progression import (
    build_all_sessions,
    _derive_subject_status,
)
from services.learning_engine.eligibility import eligible_learning_nodes
from services.learning_engine.stage_engine import compute_all_subject_states
from roadmap import get_roadmap


@pytest.fixture
def roadmap():
    return get_roadmap()


# ---------------------------------------------------------------------------
# 1. Threshold boundary: PF below threshold does NOT effectively complete
# ---------------------------------------------------------------------------

def test_pf_below_threshold_does_not_effectively_complete(roadmap):
    """PF=6 → effective_knowledge_score=60 < 70 → PF is NOT effectively
    completed → Java remains locked."""
    ctx = build_learner_context(
        onboarding={
            "current_position": "student",
            "self_assessment": {"programming_fundamentals": 6, "java": 0},
        },
    )
    assert ctx.effective_knowledge_score("programming_fundamentals") < EFFECTIVE_SUBJECT_COMPLETE_THRESHOLD
    effective = ctx.effective_completed_subject_ids(roadmap)
    assert "programming_fundamentals" not in effective

    # Java must be locked
    java_track = roadmap.get("java")
    java_status = _derive_subject_status(
        "java",
        java_track.get("subject_prerequisites", []),
        effective,
        roadmap.get_track_learning_nodes("java"),
        ctx.progress_map,
    )
    assert java_status == "locked"


# ---------------------------------------------------------------------------
# 2. Threshold boundary: PF at exact threshold DOES effectively complete
# ---------------------------------------------------------------------------

def test_pf_at_threshold_effectively_completes(roadmap):
    """PF=7 → effective_knowledge_score=70 == threshold → PF IS effectively
    completed → Java becomes eligible."""
    ctx = build_learner_context(
        onboarding={
            "current_position": "student",
            "self_assessment": {"programming_fundamentals": 7, "java": 0},
        },
    )
    score = ctx.effective_knowledge_score("programming_fundamentals")
    assert score == pytest.approx(EFFECTIVE_SUBJECT_COMPLETE_THRESHOLD)
    effective = ctx.effective_completed_subject_ids(roadmap)
    assert "programming_fundamentals" in effective

    # Java should be eligible (not locked)
    java_track = roadmap.get("java")
    java_status = _derive_subject_status(
        "java",
        java_track.get("subject_prerequisites", []),
        effective,
        roadmap.get_track_learning_nodes("java"),
        ctx.progress_map,
    )
    assert java_status in ("eligible", "active", "completed", "mastered")


# ---------------------------------------------------------------------------
# 3. PF=0 does not effectively complete PF (explicit zero test)
# ---------------------------------------------------------------------------

def test_pf_zero_does_not_effectively_complete(roadmap):
    """PF=0 → effective_knowledge_score=0 → PF is NOT in effective set."""
    ctx = build_learner_context(
        onboarding={
            "current_position": "student",
            "self_assessment": {"programming_fundamentals": 0},
        },
    )
    assert ctx.effective_knowledge_score("programming_fundamentals") == 0.0
    assert "programming_fundamentals" not in ctx.effective_completed_subject_ids(roadmap)


# ---------------------------------------------------------------------------
# 4. DSA/OS/DBMS/CN remain blocked when only PF is effectively complete
# ---------------------------------------------------------------------------

def test_downstream_subjects_blocked_when_only_pf_effective(roadmap):
    """PF=9 effectively completes PF, but Java is NOT effectively complete.
    Therefore DSA (prereq=java), OS (prereq=java), DBMS (prereq=java),
    CN (prereq=java) must all remain locked."""
    ctx = build_learner_context(
        onboarding={
            "current_position": "student",
            "self_assessment": {"programming_fundamentals": 9, "java": 1},
        },
    )
    effective = ctx.effective_completed_subject_ids(roadmap)
    assert "programming_fundamentals" in effective
    assert "java" not in effective

    for track_id in ("dsa", "operating_systems", "dbms", "computer_networks"):
        track = roadmap.get(track_id)
        if not track:
            continue
        prereqs = track.get("subject_prerequisites", [])
        status = _derive_subject_status(
            track_id,
            prereqs,
            effective,
            roadmap.get_track_learning_nodes(track_id),
            ctx.progress_map,
        )
        assert status == "locked", (
            f"{track_id} should be locked (java not complete), got {status!r}"
        )


# ---------------------------------------------------------------------------
# 5. LLD/HLD remain downstream of their full prerequisite chains
# ---------------------------------------------------------------------------

def test_lld_hld_remain_locked_with_partial_effective_completion(roadmap):
    """Even with PF+Java effectively complete, LLD (prereqs: java, dsa, os)
    and HLD (prereqs: java, dbms, os, cn, lld) remain locked."""
    ctx = build_learner_context(
        onboarding={
            "current_position": "student",
            "self_assessment": {
                "programming_fundamentals": 10, "java": 10,
                "dsa": 0, "operating_systems": 0, "dbms": 0,
                "computer_networks": 0, "lld": 0, "hld": 0,
            },
        },
    )
    effective = ctx.effective_completed_subject_ids(roadmap)
    assert "programming_fundamentals" in effective
    assert "java" in effective

    for track_id in ("lld", "hld"):
        track = roadmap.get(track_id)
        if not track:
            continue
        prereqs = track.get("subject_prerequisites", [])
        # LLD needs dsa+os; HLD needs dbms+os+cn+lld — none of those are effective
        status = _derive_subject_status(
            track_id,
            prereqs,
            effective,
            roadmap.get_track_learning_nodes(track_id),
            ctx.progress_map,
        )
        assert status == "locked", (
            f"{track_id} should be locked (missing prereqs), got {status!r}"
        )


# ---------------------------------------------------------------------------
# 6. Projects, Resume, Behavioral are independent/parallel — always eligible
# ---------------------------------------------------------------------------

def test_independent_tracks_always_eligible(roadmap):
    """Projects, Resume, Behavioral have no subject_prerequisites and should
    never be locked regardless of effective completion state."""
    ctx = build_learner_context(
        onboarding={
            "current_position": "student",
            "self_assessment": {"programming_fundamentals": 0},
        },
    )
    effective = ctx.effective_completed_subject_ids(roadmap)

    for track_id in ("projects", "behavioral", "resume"):
        track = roadmap.get(track_id)
        if not track:
            continue
        prereqs = track.get("subject_prerequisites", [])
        assert prereqs == [], f"{track_id} should have no prerequisites"
        track_nodes = roadmap.get_track_learning_nodes(track_id)
        status = _derive_subject_status(
            track_id, prereqs, effective, track_nodes, ctx.progress_map,
        )
        assert status != "locked", (
            f"{track_id} should not be locked (no prerequisites), got {status!r}"
        )


# ---------------------------------------------------------------------------
# 7. Eligibility and Subject Progression consume the SAME effective concept
# ---------------------------------------------------------------------------

def test_eligibility_and_sessions_agree_on_java_availability(roadmap):
    """When PF is effectively complete (PF=9), both:
    - the eligibility engine (via virtual_completed_node_ids) should include
      Java nodes in its eligible set, AND
    - build_all_sessions (via effective_completed_subject_ids) should mark
      Java as eligible/active, NOT locked.

    This is the core architectural invariant the fix established."""
    ctx = build_learner_context(
        onboarding={
            "current_position": "student",
            "self_assessment": {"programming_fundamentals": 9, "java": 1},
        },
    )

    # Eligibility side: Java nodes should appear in eligible set
    virtual = ctx.virtual_completed_node_ids()
    states = compute_all_subject_states(roadmap, ctx.progress_map)
    eligible = eligible_learning_nodes(
        ctx.progress_map, states,
        virtual_completed_node_ids=virtual,
    )
    eligible_tracks = {n.get("track") for n in eligible}
    assert "java" in eligible_tracks, (
        f"Eligibility engine should include Java nodes, eligible tracks: {eligible_tracks}"
    )

    # Session side: Java should not be locked
    effective_subjects = ctx.effective_completed_subject_ids(roadmap)
    sessions = build_all_sessions(
        roadmap, ctx.progress_map,
        effective_completed_subjects=effective_subjects,
    )
    java_session = sessions.get("java")
    assert java_session is not None
    assert java_session.status != "locked", (
        f"Session pipeline should mark Java as not-locked, got {java_session.status!r}"
    )

    # PF should be completed in sessions (not eligible/active)
    pf_session = sessions.get("programming_fundamentals")
    assert pf_session is not None
    assert pf_session.status in ("completed", "mastered"), (
        f"PF should be completed in session pipeline, got {pf_session.status!r}"
    )


def test_eligibility_and_sessions_agree_java_locked_at_pf0(roadmap):
    """When PF is NOT effectively complete (PF=0), both engines must agree
    Java is not available."""
    ctx = build_learner_context(
        onboarding={
            "current_position": "student",
            "self_assessment": {"programming_fundamentals": 0, "java": 0},
        },
    )

    # Eligibility: Java nodes should NOT appear
    virtual = ctx.virtual_completed_node_ids()
    states = compute_all_subject_states(roadmap, ctx.progress_map)
    eligible = eligible_learning_nodes(
        ctx.progress_map, states,
        virtual_completed_node_ids=virtual,
    )
    eligible_tracks = {n.get("track") for n in eligible}
    assert "java" not in eligible_tracks

    # Sessions: Java should be locked
    effective_subjects = ctx.effective_completed_subject_ids(roadmap)
    sessions = build_all_sessions(
        roadmap, ctx.progress_map,
        effective_completed_subjects=effective_subjects,
    )
    assert sessions["java"].status == "locked"
