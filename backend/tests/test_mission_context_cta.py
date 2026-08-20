"""Phase 3D Slice A \u2014 canonical activity_type -> CTA mapping.

Pure unit tests (no server / DB). The CTA a page renders must come entirely
from Mission Context; the frontend never infers it. This verifies the mapping
that the /missions/today/context projection returns.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.mission_context import cta_for_activity, build_mission_context  # noqa: E402


def test_cta_rules_match_frozen_contract():
    assert cta_for_activity("study")["action"] == "open_knowledge_base"
    assert cta_for_activity("coding")["action"] == "open_coding_arena"
    for t in ("quiz", "behavioral", "design", "system_design"):
        assert cta_for_activity(t)["action"] == "start_assessment"
    assert cta_for_activity("flashcards")["action"] == "open_flashcards"


def test_cta_labels_present():
    assert cta_for_activity("study")["label"] == "Open Knowledge Base"
    assert cta_for_activity("coding")["label"] == "Open Coding Arena"
    assert cta_for_activity("quiz")["label"] == "Start Assessment"


def test_cta_none_for_missing_activity():
    assert cta_for_activity(None) is None
    assert cta_for_activity("unknown_type") is None


def test_study_node_projects_to_knowledge_base_cta():
    ctx = build_mission_context("pf.intro.core")
    assert cta_for_activity(ctx.activity_type)["action"] == "open_knowledge_base"


def test_coding_node_projects_to_arena_cta():
    ctx = build_mission_context("dsa.foundations.arrays")
    assert cta_for_activity(ctx.activity_type)["action"] == "open_coding_arena"
