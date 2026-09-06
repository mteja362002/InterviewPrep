import asyncio

import pytest

import mission_engine
from mission_engine import build_mission_for_user
from models import OnboardingSelfAssessment
from services.learning_engine.builder import build_learning_recommendation
from services.learning_engine.planner import get_today_learning_node
from services.learning_engine.ranking import rank_learning_nodes
from services.learning_engine.revision import (
    get_due_revision_nodes,
    get_highest_priority_revision,
    has_due_revision,
)
from services.learning_engine.unlock import (
    first_unlockable_node,
    get_unlocked_nodes,
    is_node_unlocked,
    next_unlockable_nodes,
)


class FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    async def to_list(self, length=None):
        return list(self._rows)


class FakeCollection:
    def __init__(self, rows):
        self._rows = rows

    def find(self, query=None, projection=None):
        return FakeCursor(list(self._rows))


class FakeDB:
    def __init__(self, rows):
        self.knowledge_nodes = FakeCollection(rows)


def test_unlock_logic_respects_prerequisites():
    progress_rows = [
        {"node_id": "dsa.foundations.arrays.traversal", "status": "completed", "confidence": 8.0, "weakness_score": 20.0, "mastery": 90.0},
    ]

    assert is_node_unlocked("dsa.foundations.arrays.prefix_sum", progress_rows)
    assert not is_node_unlocked("dsa.foundations.arrays.diff_array", progress_rows)


def test_get_unlocked_and_next_unlockable_nodes():
    progress_rows = [
        {"node_id": "dsa.foundations.arrays.traversal", "status": "completed", "confidence": 8.0, "weakness_score": 20.0, "mastery": 90.0},
        {"node_id": "dsa.foundations.arrays.prefix_sum", "status": "completed", "confidence": 7.0, "weakness_score": 30.0, "mastery": 80.0},
    ]

    unlocked = get_unlocked_nodes(progress_rows)
    next_nodes = next_unlockable_nodes(progress_rows)

    assert any(node["id"] == "dsa.foundations.arrays.prefix_sum" for node in unlocked)
    assert any(node["id"] == "dsa.foundations.arrays.diff_array" for node in next_nodes)
    # As of the 2026 curriculum sync, Programming Fundamentals is track 0 with no
    # prerequisites, so it — not DSA — is now the very first unlockable node
    # across the whole roadmap.
    assert first_unlockable_node(progress_rows)["id"] == "pf.intro.core"


def test_first_time_beginner_starts_from_programming_fundamentals():
    onboarding = {
        "current_position": "student",
        "self_assessment": {"dsa": 8, "java": 8, "lld": 8, "hld": 8,
                            "operating_systems": 8, "dbms": 8, "computer_networks": 8,
                            "projects": 10, "behavioral": 10, "resume": 10},
    }

    recommendation = asyncio.run(
        get_today_learning_node("user-1", db=FakeDB([]), onboarding=onboarding, recent_completions=[])
    )

    assert recommendation["track"] == "programming_fundamentals"

    zero_ratings = {
        "current_position": "5+",
        "self_assessment": {"dsa": 0, "java": 0, "lld": 0, "hld": 0,
                            "operating_systems": 0, "dbms": 0, "computer_networks": 0,
                            "projects": 10, "behavioral": 10, "resume": 10},
    }
    recommendation = asyncio.run(
        get_today_learning_node("user-1", db=FakeDB([]), onboarding=zero_ratings, recent_completions=[])
    )

    assert recommendation["track"] == "programming_fundamentals"


def test_onboarding_self_assessment_accepts_zero_as_no_knowledge():
    assessment = OnboardingSelfAssessment(dsa=0)

    assert assessment.dsa == 0
    assert assessment.java == 0


def test_ranking_prefers_low_confidence_and_high_weakness():
    nodes = [
        {"id": "node-1", "difficulty": "easy", "estimated_minutes": 20, "company_importance": {"google": 2}},
        {"id": "node-2", "difficulty": "hard", "estimated_minutes": 60, "company_importance": {"google": 5}},
    ]
    progress = {
        "node-1": {"confidence": 8.0, "weakness_score": 20.0, "mastery": 80.0},
        "node-2": {"confidence": 2.0, "weakness_score": 80.0, "mastery": 20.0},
    }

    ranked = rank_learning_nodes(nodes, progress, target_companies=["google"])
    assert ranked[0]["id"] == "node-2"


def test_planner_returns_revision_before_other_candidates():
    rows = [
        {"node_id": "dsa.foundations.arrays.traversal", "status": "completed", "confidence": 8.0, "weakness_score": 20.0, "mastery": 90.0},
        {"node_id": "dsa.foundations.arrays.prefix_sum", "status": "not_started", "confidence": 3.0, "weakness_score": 70.0, "mastery": 20.0},
        {"node_id": "dsa.foundations.arrays.diff_array", "status": "not_started", "confidence": 6.0, "weakness_score": 50.0, "mastery": 40.0, "next_revision": "2026-07-20T00:00:00+00:00", "revision_stage": 1},
    ]

    recommendation = asyncio.run(get_today_learning_node("user-1", db=FakeDB(rows)))
    assert recommendation["node_id"] == "dsa.foundations.arrays.diff_array"


def test_builder_output_shape():
    node = {
        "id": "dsa.foundations.arrays.prefix_sum",
        "track": "dsa",
        "module": "dsa.foundations",
        "difficulty": "medium",
        "estimated_minutes": 25,
        "label": "Prefix Sum",
    }
    recommendation = build_learning_recommendation(node, progress={"confidence": 3.0, "weakness_score": 70.0, "mastery": 25.0})

    assert recommendation["node_id"] == "dsa.foundations.arrays.prefix_sum"
    assert recommendation["recommendation_type"] == "learning"
    assert recommendation["difficulty"] == "medium"
    assert recommendation["estimated_minutes"] == 25
    assert recommendation["reason"]


def test_planner_builds_support_and_core_recommendations_from_roadmap():
    rows = [
        {"node_id": "dsa.foundations.arrays.prefix_sum", "status": "completed", "confidence": 7.0, "weakness_score": 30.0, "mastery": 80.0},
        {"node_id": "lld.patterns.creational.factory.overview", "status": "not_started", "confidence": 2.0, "weakness_score": 80.0, "mastery": 20.0, "track": "lld"},
    ]
    recommendation = asyncio.run(get_today_learning_node("user-1", db=FakeDB(rows)))

    assert recommendation is not None
    # The support task should reinforce a topically-related, unlocked node in
    # the roadmap graph when one exists, rather than jumping straight to an
    # unrelated cross-track pick (cross-track fallback only applies when no
    # related candidate qualifies).
    assert recommendation.get("support_node") is not None
    assert recommendation["support_node"] != recommendation.get("node_id")


def test_revision_selection_uses_due_reviews():
    rows = [
        {"node_id": "dsa.foundations.arrays.traversal", "status": "completed", "confidence": 8.0, "weakness_score": 20.0, "mastery": 90.0},
        {"node_id": "dsa.foundations.arrays.prefix_sum", "status": "completed", "confidence": 6.0, "weakness_score": 50.0, "mastery": 70.0, "next_revision": "2026-07-20T00:00:00+00:00", "revision_stage": 2},
    ]

    due_nodes = get_due_revision_nodes("user-1", progress_rows=rows)
    assert len(due_nodes) == 1
    assert has_due_revision("user-1", progress_rows=rows)
    assert get_highest_priority_revision("user-1", progress_rows=rows)["node_id"] == "dsa.foundations.arrays.prefix_sum"


def test_mission_engine_uses_learning_recommendation_when_provided():
    mission, _ = build_mission_for_user(
        "user-1",
        onboarding={"current_position": "5+", "target_companies": ["google"], "self_assessment": {"dsa": 6, "java": 5, "lld": 4, "hld": 4}},
        knowledge=[],
        revisions_due=[],
        recent_feedback=[],
        ds="2026-07-23",
        knowledge_nodes={},
        learning_recommendation={
            "track": "java",
            "label": "Concurrency",
            "difficulty": "hard",
            "subtopic": "Threads",
            "node_id": "java.concurrency.threads",
        },
    )

    assert mission.focus_topic == "java"
    assert mission.difficulty == "hard"
    assert "Concurrency" in mission.focus_area
    assert any(task.node_id == "java.concurrency.threads" for task in mission.tasks)


def test_mission_engine_does_not_use_legacy_selection_when_recommendation_is_provided(monkeypatch):
    def fail_select_primary_topic(*args, **kwargs):
        raise AssertionError("Legacy topic selection must not run when recommendation is provided")

    monkeypatch.setattr(mission_engine, "select_primary_topic", fail_select_primary_topic)

    mission, _ = build_mission_for_user(
        "user-1",
        onboarding={"current_position": "5+", "target_companies": ["google"], "self_assessment": {"dsa": 6, "java": 5, "lld": 4, "hld": 4}},
        knowledge=[],
        revisions_due=[],
        recent_feedback=[],
        ds="2026-07-23",
        knowledge_nodes={},
        learning_recommendation={
            "track": "java",
            "label": "Concurrency",
            "difficulty": "hard",
            "subtopic": "Threads",
            "node_id": "java.concurrency.threads",
        },
    )

    assert mission.focus_topic == "java"
    assert mission.difficulty == "hard"
    assert any(task.node_id == "java.concurrency.threads" for task in mission.tasks)


def test_mission_engine_uses_support_recommendation_when_provided(monkeypatch):
    class FakeRandom:
        def choice(self, seq):
            return seq[0]

    monkeypatch.setattr(mission_engine, "_seeded_random", lambda user_id, ds: FakeRandom())

    mission, _ = build_mission_for_user(
        "user-1",
        onboarding={"target_companies": ["google"], "self_assessment": {"dsa": 6, "java": 5, "lld": 4, "hld": 4}},
        knowledge=[],
        revisions_due=[],
        recent_feedback=[],
        ds="2026-07-23",
        knowledge_nodes={},
        learning_recommendation={
            "track": "java",
            "label": "Concurrency",
            "difficulty": "hard",
            "subtopic": "Threads",
            "support_track": "lld",
        },
    )

    support_topics = [task.topic for task in mission.tasks if task.kind == "study"]
    assert "lld" in support_topics


def test_mission_engine_does_not_fallback_to_legacy_support_topic_when_track_is_valid_but_no_unlocked_node(monkeypatch):
    class FakeRandom:
        def choice(self, seq):
            return seq[0]

    monkeypatch.setattr(mission_engine, "_seeded_random", lambda user_id, ds: FakeRandom())
    monkeypatch.setattr(mission_engine, "_find_roadmap_node_by_id", lambda node_id: None)
    monkeypatch.setattr(mission_engine, "_select_unlocked_roadmap_node", lambda track, nodes: None)

    mission, _ = build_mission_for_user(
        "user-1",
        onboarding={"target_companies": ["google"], "self_assessment": {"dsa": 6, "java": 5, "lld": 4, "hld": 4}},
        knowledge=[],
        revisions_due=[],
        recent_feedback=[],
        ds="2026-07-23",
        knowledge_nodes={},
        learning_recommendation={
            "track": "java",
            "label": "Concurrency",
            "difficulty": "hard",
            "subtopic": "Threads",
            "support_track": "lld",
        },
    )

    assert not any(task.kind == "study" and task.topic == "lld" for task in mission.tasks)


def test_mission_engine_does_not_fallback_to_legacy_core_topic_when_no_unlocked_core_node_available(monkeypatch):
    class FakeRandom:
        def choice(self, seq):
            return seq[0]

    monkeypatch.setattr(mission_engine, "_seeded_random", lambda user_id, ds: FakeRandom())
    monkeypatch.setattr(mission_engine, "_find_roadmap_node_by_id", lambda node_id: None)
    monkeypatch.setattr(mission_engine, "_select_unlocked_roadmap_node", lambda track, nodes: None)

    mission, _ = build_mission_for_user(
        "user-1",
        onboarding={"target_companies": ["google"], "self_assessment": {"dsa": 6, "java": 5, "lld": 4, "hld": 4}, "daily_study_hours": 3},
        knowledge=[],
        revisions_due=[],
        recent_feedback=[],
        ds="2026-07-23",
        knowledge_nodes={},
        learning_recommendation={
            "track": "java",
            "label": "Concurrency",
            "difficulty": "hard",
            "subtopic": "Threads",
        },
    )

    assert not any(task.kind == "study" and task.title.startswith("Read:") for task in mission.tasks)


def test_mission_engine_preserves_existing_selection_when_recommendation_is_none(monkeypatch):
    def fake_select_primary_topic(*args, **kwargs):
        return "lld", "Memory Management", "easy"

    monkeypatch.setattr(mission_engine, "select_primary_topic", fake_select_primary_topic)

    mission, _ = build_mission_for_user(
        "user-1",
        onboarding={"target_companies": ["google"], "self_assessment": {"dsa": 6, "java": 5, "lld": 4, "hld": 4}},
        knowledge=[],
        revisions_due=[],
        recent_feedback=[],
        ds="2026-07-23",
        knowledge_nodes={},
        learning_recommendation=None,
    )

    assert mission.focus_topic == "lld"
    assert mission.difficulty == "easy"
    assert "Memory Management" in mission.focus_area


def test_revision_task_node_id_propagates():
    mission, _ = build_mission_for_user(
        "user-1",
        onboarding={"target_companies": ["google"], "self_assessment": {"dsa": 6, "java": 5, "lld": 4, "hld": 4}},
        knowledge=[],
        revisions_due=[
            {"task_title": "Revise: Prefix Sum", "topic": "dsa", "node_id": "dsa.foundations.arrays.prefix_sum"},
        ],
        recent_feedback=[],
        ds="2026-07-23",
        knowledge_nodes={},
        learning_recommendation=None,
    )

    revise_task = next((t for t in mission.tasks if t.kind == "revise"), None)
    assert revise_task is not None
    assert revise_task.node_id == "dsa.foundations.arrays.prefix_sum"
