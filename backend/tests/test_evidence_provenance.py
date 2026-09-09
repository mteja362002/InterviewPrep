"""Deterministic acceptance tests for the forward evidence boundary."""
import asyncio
from copy import deepcopy
from types import SimpleNamespace
import sys

import pytest

from models import OnboardingSelfAssessment, KnowledgeConfidenceUpdate, KnowledgeStatusUpdate, KnowledgeAttemptUpdate
from roadmap import get_roadmap
from services.evidence import certified_fields, legacy_fields, actual_row, planner_row
from services.progress_engine import build_canonical_progress, planner_progress_rows, seed_knowledge_nodes_from_self_assessment
from services.progress_repository import upsert_progress_fields, upsert_progress_from_score
from services.learning_engine.context import build_learner_context
from services.learning_engine.planner import get_today_learning_node
from services.revision_engine import mark_node_for_revision, get_revisions_for_user
from tests.evidence_fixtures import certified

ROADMAP = get_roadmap()
NODE = ROADMAP.get_track_learning_nodes("java")[0]["id"]
BASELINES = [("programming_fundamentals", 0), ("programming_fundamentals", 7),
             ("programming_fundamentals", 9), ("programming_fundamentals", 10),
             ("java", 7), ("dsa", 9), ("operating_systems", 6), ("dbms", 5),
             ("computer_networks", 4), ("lld", 8), ("hld", 3)]


class Cursor:
    def __init__(self, rows): self.rows = deepcopy(rows)
    async def to_list(self, length=None): return self.rows[:length] if length else self.rows
    def sort(self, *args): return self
    def limit(self, count): self.rows = self.rows[:count]; return self


class Collection:
    def __init__(self, rows=()): self.rows = deepcopy(list(rows)); self.writes = []
    def find(self, query=None, projection=None):
        return Cursor([row for row in self.rows if all(row.get(k) == v for k, v in (query or {}).items())])
    async def find_one(self, query, projection=None):
        return next(iter(await self.find(query).to_list()), None)
    async def update_one(self, query, update, upsert=False):
        self.writes.append(deepcopy(update))
        def matches(row):
            for path, expected in query.items():
                value = row
                for key in path.split("."):
                    value = value.get(key) if isinstance(value, dict) else None
                if isinstance(expected, dict) and "$exists" in expected:
                    if (value is not None) != expected["$exists"]: return False
                elif value != expected: return False
            return True
        row = next((row for row in self.rows if matches(row)), None)
        if row is None:
            if not upsert: return
            row = deepcopy(query); self.rows.append(row)
        for op, fields in update.items():
            for path, value in fields.items():
                parent = row
                keys = path.split(".")
                for key in keys[:-1]: parent = parent.setdefault(key, {})
                if op == "$inc": parent[keys[-1]] = parent.get(keys[-1], 0) + value
                elif op == "$set": parent[keys[-1]] = deepcopy(value)
                else: raise AssertionError(op)
    async def replace_one(self, query, doc):
        row = next(row for row in self.rows if all(row.get(k) == v for k, v in query.items()))
        row.clear(); row.update(deepcopy(doc))
    async def insert_one(self, doc): self.rows.append(deepcopy(doc))
    async def delete_many(self, query): self.writes.append({"delete_many": query})


def db_with(rows=(), scores=None):
    return SimpleNamespace(
        knowledge_nodes=Collection(rows),
        users=Collection([{"id": "u", "roadmap_version": ROADMAP.version}]),
        onboarding=Collection([{"user_id": "u", "self_assessment": scores or {}}]),
        daily_missions=Collection(),
    )


def legacy():
    return {"user_id": "u", "node_id": NODE, "roadmap_version": ROADMAP.version,
            "mastery_percentage": 70, "confidence": 7, "status": "completed",
            "attempts": 3, "actual_solve_minutes": 12,
            "completion_date": "2026-01-01T12:00:00+00:00",
            "last_revision": "2026-01-03", "next_revision": "2026-01-10", "revision_stage": 2,
            "notes": "retained note", "bookmarked": True}


@pytest.mark.parametrize("track,rating", BASELINES)
def test_baseline_without_evidence_has_zero_actual_and_no_persisted_seed(track, rating):
    scores = OnboardingSelfAssessment(**{track: rating}).model_dump()
    onboarding = {"self_assessment": scores, "current_position": "student"}
    db = db_with(scores=scores)
    assert asyncio.run(seed_knowledge_nodes_from_self_assessment(db, "u", scores, ROADMAP)) == 0
    runtime = planner_progress_rows(ROADMAP, [], onboarding)
    context = build_learner_context(onboarding=onboarding, progress_rows=runtime)
    assert context.effective_knowledge_score(track) == rating * 10
    assert context.track_completion_count(track) == 0
    assert context.track_average_mastery(track) is None
    roll = build_canonical_progress(ROADMAP, {}, onboarding)[track]
    assert roll["onboarding_baseline"] == rating * 10
    assert roll["mastery_percentage"] == roll["completed_topics"] == 0
    assert roll["legacy_progress"] is None
    assert db.knowledge_nodes.rows == db.knowledge_nodes.writes == []
    if track == "programming_fundamentals":
        assert (track in context.effective_completed_subject_ids(ROADMAP)) == (rating >= 7)
        pick = asyncio.run(get_today_learning_node("u", db=db, onboarding=onboarding))
        assert pick and (pick["track"] != track if rating >= 7 else pick["track"] == track)


@pytest.mark.parametrize("track", list(OnboardingSelfAssessment.model_fields))
def test_all_eight_actual_and_baseline_remain_separate(track):
    nid = ROADMAP.get_track_learning_nodes(track)[0]["id"]
    row = certified({"node_id": nid, "mastery_percentage": 42, "confidence": 4.2, "status": "completed"})
    onboarding = {"self_assessment": {track: 8}}
    rolls = build_canonical_progress(ROADMAP, {nid: row}, onboarding)
    assert rolls[nid]["mastery_percentage"] == 42
    assert rolls[track]["onboarding_baseline"] == 80
    assert rolls[track]["completed_topics"] == 1
    assert rolls[nid]["legacy_progress"] is None
    ctx = build_learner_context(onboarding=onboarding, progress_rows=[row])
    assert ctx.track_average_mastery(track) == 42
    assert ctx.track_completion_count(track) == 1
    assert ctx.effective_knowledge_score(track) == pytest.approx((42 + 2 * 80) / 3)


def test_legacy_with_dates_attempts_and_wrong_track_never_certifies_mastery():
    raw = {**legacy(), "track": "dsa"}
    before = deepcopy(raw)
    rolls = build_canonical_progress(ROADMAP, {NODE: raw}, {"self_assessment": {"java": 7}})
    assert rolls[NODE]["mastery_percentage"] == rolls[NODE]["completed_topics"] == 0
    assert rolls[NODE]["legacy_progress"]["stored_fields"] == legacy_fields(raw)
    assert rolls[NODE]["legacy_progress"]["classification"] == "unverified_legacy"
    assert rolls[NODE]["legacy_progress"]["mastery_percentage"] == 70
    ctx = build_learner_context(onboarding={"self_assessment": {"java": 7}}, progress_rows=[raw])
    assert ctx.track_completion_count("java") == ctx.track_completion_count("dsa") == 0
    assert ctx.effective_knowledge_score("java") == 70
    assert ctx.progress_map[NODE]["planner_progress_source"] == "unverified_legacy"
    assert raw == before


def test_subject_mastery_of_42_is_preserved_beside_baseline_of_80():
    rows = {node["id"]: certified({"node_id": node["id"], "mastery_percentage": 42,
                                    "confidence": 4.2, "status": "in_progress"})
            for node in ROADMAP.get_track_learning_nodes("java")}
    roll = build_canonical_progress(ROADMAP, rows, {"self_assessment": {"java": 8}})["java"]
    assert roll["mastery_percentage"] == 42
    assert roll["onboarding_baseline"] == 80
    assert roll["completed_topics"] == 0


def test_later_task_gain_preserves_unknown_seventy_and_only_uses_certified_prior():
    from routes_missions import _record_completed_task_progress
    from mission_engine import apply_knowledge_gain
    raw = legacy(); db = db_with([raw])
    async def run():
        await _record_completed_task_progress(db, "u", {"node_id": NODE, "topic": "java", "kind": "study"},
                                              "easy", {"java": 9}, "2026-09-09T01:00:00+00:00")
        written = db.knowledge_nodes.rows[0]
        assert legacy_fields(written) == legacy_fields(raw)
        actual = certified_fields(written)
        expected = apply_knowledge_gain(0, "easy", "study")
        assert actual["mastery_percentage"] == expected
        assert actual["mastery_percentage"] != apply_knowledge_gain(70, "easy", "study")
        assert actual["status"] == "completed"
        assert actual["completion_date"] == "2026-09-09T01:00:00+00:00"
        assert written["track"] == "java"
        roll = build_canonical_progress(ROADMAP, {NODE: written})[NODE]
        assert roll["mastery_percentage"] == expected
        assert roll["legacy_progress"]["mastery_percentage"] == 70
        await _record_completed_task_progress(db, "u", {"node_id": NODE, "topic": "java", "kind": "study"},
                                              "easy", {"java": 1}, "2026-09-09T02:00:00+00:00")
        assert certified_fields(written)["mastery_percentage"] == apply_knowledge_gain(expected, "easy", "study")
        assert legacy_fields(written) == legacy_fields(raw)
    asyncio.run(run())


def test_new_status_records_completion_without_certifying_unknown_mastery(monkeypatch):
    from routes_roadmap import update_status
    raw = legacy(); db = db_with([raw]); monkeypatch.setitem(sys.modules, "server", SimpleNamespace(db=db))
    asyncio.run(update_status(NODE, KnowledgeStatusUpdate(status="completed"), user={"id": "u"}))
    written = db.knowledge_nodes.rows[0]
    assert legacy_fields(written) == legacy_fields(raw)
    assert "mastery_percentage" not in certified_fields(written)
    roll = build_canonical_progress(ROADMAP, {NODE: written})[NODE]
    assert roll["mastery_percentage"] == 0
    assert roll["completed_topics"] == 1


def test_new_revision_records_its_date_without_changing_historical_revision_facts():
    from routes_missions import _record_completed_task_progress
    raw = legacy(); db = db_with([raw])
    now = "2026-09-09T03:00:00+00:00"
    asyncio.run(_record_completed_task_progress(db, "u", {"node_id": NODE, "topic": "java", "kind": "revise"},
                                                 "easy", {"java": 9}, now))
    assert legacy_fields(db.knowledge_nodes.rows[0]) == legacy_fields(raw)
    assert certified_fields(db.knowledge_nodes.rows[0])["last_revision"] == now


def test_problem_feedback_averages_only_attributable_confidence(monkeypatch):
    from routes_missions import submit_problem_feedback
    from models import ProblemFeedbackPayload
    raw = legacy(); db = db_with([raw])
    db.problem_assignments = Collection([{"id": "a", "user_id": "u", "mission_id": "m",
                                         "problem_id": "test-problem", "pattern": "arrays"}])
    db.daily_missions = Collection([{"id": "m", "tasks": [{"kind": "practice", "pattern": "arrays", "node_id": NODE}]}])
    db.problem_feedback = Collection(); db.activity_events = Collection()
    monkeypatch.setitem(sys.modules, "server", SimpleNamespace(db=db))
    payload = ProblemFeedbackPayload(difficulty_rating="easy", solved_status="without_hints",
                                     confidence=8, time_taken_minutes=15)
    async def run():
        await submit_problem_feedback("a", payload, user={"id": "u"})
        written = db.knowledge_nodes.rows[0]
        assert certified_fields(written)["confidence"] == 2
        assert certified_fields(written)["mastery_percentage"] == 20
        assert legacy_fields(written) == legacy_fields(raw)
        assert len(db.problem_feedback.rows) == 1
        assert written["certified_progress"]["field_sources"]["confidence"]["source"] == "problem_feedback"
    asyncio.run(run())


def test_notes_and_bookmarks_do_not_certify_unknown_progress(monkeypatch):
    from routes_roadmap import update_notes, toggle_bookmark
    from models import KnowledgeNoteUpdate
    raw = legacy(); db = db_with([raw]); monkeypatch.setitem(sys.modules, "server", SimpleNamespace(db=db))
    async def run():
        await update_notes(NODE, KnowledgeNoteUpdate(notes="new note"), user={"id": "u"})
        await toggle_bookmark(NODE, user={"id": "u"})
        written = db.knowledge_nodes.rows[0]
        assert written["notes"] == "new note"
        assert written["bookmarked"] is False
        assert certified_fields(written) == {}
        assert legacy_fields(written) == legacy_fields(raw)
    asyncio.run(run())


def test_explicit_new_confidence_is_independent_measurement_and_preserves_legacy(monkeypatch):
    from routes_roadmap import update_confidence
    raw = legacy(); db = db_with([raw]); monkeypatch.setitem(sys.modules, "server", SimpleNamespace(db=db))
    asyncio.run(update_confidence(NODE, KnowledgeConfidenceUpdate(confidence=8), user={"id": "u"}))
    written = db.knowledge_nodes.rows[0]
    assert certified_fields(written)["mastery_percentage"] == 80
    assert legacy_fields(written) == legacy_fields(raw)
    assert written["certified_progress"]["field_sources"]["mastery_percentage"]["source"] == "confidence_update"


def test_attempt_and_revision_facts_preserved_without_certifying_old_scores(monkeypatch):
    from routes_roadmap import record_attempt
    raw = legacy(); db = db_with([raw]); monkeypatch.setitem(sys.modules, "server", SimpleNamespace(db=db))
    async def run():
        await asyncio.gather(*(record_attempt(NODE, KnowledgeAttemptUpdate(actual_minutes=5), user={"id": "u"}) for _ in range(3)))
        queue = await get_revisions_for_user(db, "u", ROADMAP.version, due_only=False)
        assert queue[0]["evidence_classification"] == "unverified_legacy"
        assert queue[0]["next_review_date"] == raw["next_revision"]
        await mark_node_for_revision(db, "u", ROADMAP.version, NODE)
        written = db.knowledge_nodes.rows[0]
        assert legacy_fields(written) == legacy_fields(raw)
        assert certified_fields(written)["attempts"] == 3
        assert build_canonical_progress(ROADMAP, {NODE: written})[NODE]["status"] == "in_progress"
        assert planner_row(written)["status"] == raw["status"]
        assert certified_fields(written)["actual_solve_minutes"] == 15
        assert "mastery_percentage" not in certified_fields(written)
        assert certified_fields(written)["revision_stage"] == 0
        queue = await get_revisions_for_user(db, "u", ROADMAP.version, due_only=False)
        assert queue[0]["evidence_classification"] == "certified_actual"
    asyncio.run(run())


def test_runtime_baseline_cannot_be_counted_as_actual_or_mislabelled_as_legacy():
    onboarding = {"self_assessment": OnboardingSelfAssessment(java=7).model_dump()}
    runtime = planner_progress_rows(ROADMAP, [], onboarding)
    assert all(not certified_fields(row) and not legacy_fields(row) for row in runtime)
    roll = build_canonical_progress(ROADMAP, {row["node_id"]: row for row in runtime}, onboarding)["java"]
    assert roll["mastery_percentage"] == 0
    assert roll["onboarding_baseline"] == 70
    assert roll["legacy_progress"] is None


def test_independent_tracks_have_no_onboarding_baseline():
    onboarding = {"self_assessment": OnboardingSelfAssessment().model_dump()}
    ctx = build_learner_context(onboarding=onboarding)
    rolls = build_canonical_progress(ROADMAP, {}, onboarding)
    for track in ("projects", "behavioral", "resume"):
        assert track not in ctx.onboarding_scores
        assert ctx.effective_knowledge_score(track) == 0
        assert rolls[track]["onboarding_baseline"] is None


def test_unsupported_sources_missing_stamps_and_wrong_version_are_excluded():
    row = certified({"node_id": NODE, "mastery_percentage": 99})
    for mutation in ("missing_stamp", "unknown_source", "wrong_version"):
        unknown = deepcopy(row)
        if mutation == "missing_stamp": unknown["certified_progress"]["field_sources"] = {}
        elif mutation == "unknown_source": unknown["certified_progress"]["field_sources"]["mastery_percentage"]["source"] = "onboarding"
        else: unknown["roadmap_version"] = "unknown"
        assert build_canonical_progress(ROADMAP, {NODE: unknown})[NODE]["mastery_percentage"] == 0


def test_unknown_track_identity_is_inspectable_but_not_in_actual_totals(monkeypatch):
    from routes_roadmap import get_legacy_progress
    raw = legacy(); raw.pop("roadmap_version")
    db = db_with([raw]); monkeypatch.setitem(sys.modules, "server", SimpleNamespace(db=db))
    result = asyncio.run(get_legacy_progress(user={"id": "u"}))
    assert result["records"][0]["identity_resolved"] is False
    assert result["records"][0]["stored_fields"]["mastery_percentage"] == 70


def test_kb_api_rollups_readiness_and_mentor_exclude_legacy(monkeypatch):
    from routes_roadmap import get_progress, get_summary
    from routes_missions import _get_knowledge
    from ai_mentor.context_builder import _load_progress, _summary_progress
    raw = legacy(); db = db_with([raw], {"java": 7}); monkeypatch.setitem(sys.modules, "server", SimpleNamespace(db=db))
    async def run():
        result = await get_progress(user={"id": "u"})
        java = next(track for track in result["tracks"] if track["id"] == "java")["progress"]
        assert java["mastery_percentage"] == 0
        assert java["onboarding_baseline"] == 70
        assert java["legacy_progress"] is not None
        summary = await get_summary(user={"id": "u"})
        assert summary["overall"]["completed_topics"] == 0
        assert await _get_knowledge(db, "u") == []
        assert await _load_progress(db, "u") == []
        mentor = await _summary_progress(db, "u", ROADMAP)
        assert mentor["nodes_completed"] == 0
        assert mentor["unverified_legacy_nodes"] == 1
    asyncio.run(run())


def test_all_subject_completion_is_certified_or_explicit_planner_compatibility():
    rows = [certified({"node_id": node["id"], "status": "completed", "mastery_percentage": 100})
            for node in ROADMAP.get_track_learning_nodes("java")]
    ctx = build_learner_context(progress_rows=rows)
    assert "java" in ctx.effective_completed_subject_ids(ROADMAP)
    assert ctx.track_completion_count("java") == len(rows)
    assert build_canonical_progress(ROADMAP, {r["node_id"]: r for r in rows})["java"]["completion_pct"] == 100


def test_onboarding_update_does_not_overwrite_actual_or_legacy_and_invalidates_targeted_mission(monkeypatch):
    from models import OnboardingPayload, OnboardingRecord
    from routes_user import submit_onboarding
    import services.roadmap_progress
    raw = {**legacy(), **certified({"node_id": NODE, "mastery_percentage": 30, "status": "in_progress"})}
    old = OnboardingRecord(interview_target_date="2027-01-01", estimated_prep_days=100, user_id="u", target_companies=["google"], current_position="student", daily_study_hours=2,
                           self_assessment=OnboardingSelfAssessment(java=7)).model_dump()
    db = db_with([raw]); db.onboarding = Collection([old])
    monkeypatch.setitem(sys.modules, "server", SimpleNamespace(db=db))
    async def initialize(*args): pass
    monkeypatch.setattr(services.roadmap_progress, "initialize_roadmap_progress_for_user", initialize)
    async def run():
        payload = OnboardingPayload(interview_target_date="2027-01-01", target_companies=["google"], current_position="student", daily_study_hours=2,
                                     self_assessment=OnboardingSelfAssessment(java=9))
        await submit_onboarding(payload, user={"id": "u"})
        assert db.knowledge_nodes.rows == [raw]
        assert certified_fields(raw)["mastery_percentage"] == 30
        assert db.onboarding.rows[0]["self_assessment"]["java"] == 9
        assert len(db.daily_missions.writes) == 1
        await submit_onboarding(payload, user={"id": "u"})
        assert len(db.daily_missions.writes) == 1
    asyncio.run(run())
