"""Phase 3C.1 — MissionContext single-source-of-truth object.

Pure unit tests (no server / DB) against the real roadmap.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.mission_context import build_mission_context, MissionContext  # noqa: E402


def test_coding_node_builds_coding_context_and_opens_arena():
    ctx = build_mission_context("dsa.foundations.arrays", target_companies=["google"])
    assert isinstance(ctx, MissionContext)
    assert ctx.activity_type == "coding"
    assert ctx.assessment_type == "coding"
    assert ctx.subject == "dsa"
    assert ctx.coding_pattern == "arrays"
    assert ctx.learning_stage == "foundation"
    assert ctx.knowledge_base_node == "dsa.foundations.arrays"
    assert ctx.representative_problem_ids, "coding node should expose representative problems"
    assert ctx.opens_arena is True
    assert ctx.opens_knowledge_base is False


def test_study_node_opens_kb_and_has_no_representative_problems():
    ctx = build_mission_context("pf.intro.core")
    assert ctx.activity_type == "study"
    assert ctx.opens_knowledge_base is True
    assert ctx.opens_arena is False
    assert ctx.representative_problem_ids == []


def test_representative_problems_never_leak_other_topics_or_stages():
    # All representative problems for a foundation coding node must belong to
    # that node's own pattern AND its learning stage (no future-topic leak,
    # no stage mixing).
    import problem_bank as pb
    ctx = build_mission_context("dsa.foundations.arrays")
    by_id = {p["id"]: p for p in pb.problems_by_pattern("arrays")}
    for pid in ctx.representative_problem_ids:
        assert pid in by_id, f"{pid} is not an arrays problem"
        assert by_id[pid].get("learning_stage") == "foundation"


def test_unknown_node_returns_none():
    assert build_mission_context("does.not.exist") is None


def test_context_is_json_serialisable():
    ctx = build_mission_context("dsa.foundations.arrays")
    d = ctx.to_dict()
    assert d["node_id"] == "dsa.foundations.arrays"
    assert d["activity_type"] == "coding"
    assert isinstance(d["representative_problem_ids"], list)
