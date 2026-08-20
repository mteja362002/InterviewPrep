"""Phase 3C — Mission → Assessment workflow tests.

Pure unit tests for the deterministic orchestration helpers in
routes_mission_assessment: workflow state transitions, the assessment-context
derivation (reuses mission node/difficulty), the completion gate, and
backward compatibility for missions without a linked assessment.

The HTTP endpoints themselves are validated by the live-API testing agent.
"""
import asyncio

import pytest
from fastapi import HTTPException

import routes_mission_assessment as rma


def _mission(*, tasks, status="in_progress", assessment_id=None, difficulty="medium"):
    return {
        "id": "m1", "user_id": "u1", "status": status, "difficulty": difficulty,
        "focus_topic": "arrays", "tasks": tasks, "assessment_id": assessment_id,
    }


def _task(kind, completed, node_id=None):
    return {"id": f"{kind}-{node_id or '0'}", "kind": kind, "completed": completed,
            "node_id": node_id}


# --------------------------------------------------------------------------- #
class TestWorkflowState:
    def test_mission_started(self):
        m = _mission(tasks=[_task("study", False), _task("practice", False)])
        assert rma._workflow_state(m, None) == "mission_started"

    def test_study_complete(self):
        m = _mission(tasks=[_task("study", True), _task("practice", False)])
        assert rma._workflow_state(m, None) == "study_complete"

    def test_assessment_available(self):
        m = _mission(tasks=[_task("study", True), _task("practice", True)])
        assert rma._workflow_state(m, None) == "assessment_available"

    def test_assessment_in_progress(self):
        m = _mission(tasks=[_task("study", True), _task("practice", True)])
        assert rma._workflow_state(m, "started") == "assessment_in_progress"
        assert rma._workflow_state(m, "submitted") == "assessment_in_progress"

    def test_assessment_completed(self):
        m = _mission(tasks=[_task("study", True), _task("practice", True)])
        assert rma._workflow_state(m, "completed") == "assessment_completed"

    def test_mission_completed_terminal(self):
        m = _mission(tasks=[_task("study", True)], status="completed")
        assert rma._workflow_state(m, "completed") == "mission_completed"


# --------------------------------------------------------------------------- #
class TestTasksAndContext:
    def test_tasks_all_complete(self):
        assert rma._tasks_all_complete(_mission(tasks=[_task("study", True), _task("practice", True)]))
        assert not rma._tasks_all_complete(_mission(tasks=[_task("study", True), _task("practice", False)]))
        assert not rma._tasks_all_complete(_mission(tasks=[]))

    def test_context_prefers_coding_node(self):
        m = _mission(tasks=[
            _task("study", True, node_id="dsa.arrays.core"),
            _task("practice", True, node_id="dsa.sliding_window.core"),
        ])
        ctx = rma._derive_assessment_context(m)
        assert ctx["node_id"] == "dsa.sliding_window.core"
        assert ctx["difficulty"] == "medium"

    def test_context_falls_back_to_study_then_topic(self):
        m = _mission(tasks=[_task("study", True, node_id="dsa.arrays.core")])
        assert rma._derive_assessment_context(m)["node_id"] == "dsa.arrays.core"
        m2 = _mission(tasks=[_task("practice", True)])  # no node ids
        assert rma._derive_assessment_context(m2)["node_id"] == "arrays"  # focus_topic


# --------------------------------------------------------------------------- #
class _FakeAssessment:
    def __init__(self, status):
        self.status = status


class TestCompletionGate:
    def test_no_linked_assessment_allows_completion(self):
        # Backward compatible: old missions complete freely.
        m = _mission(tasks=[_task("study", True)], assessment_id=None)
        asyncio.run(rma.assert_assessment_allows_completion(None, m, "u1"))  # no raise

    def test_incomplete_assessment_blocks_completion(self, monkeypatch):
        m = _mission(tasks=[_task("study", True)], assessment_id="a1")

        async def fake_get(user_id, aid):
            return _FakeAssessment("submitted")
        monkeypatch.setattr(rma.assessment_history, "get", fake_get)
        with pytest.raises(HTTPException) as ei:
            asyncio.run(rma.assert_assessment_allows_completion(None, m, "u1"))
        assert ei.value.status_code == 409

    def test_completed_assessment_allows_completion(self, monkeypatch):
        m = _mission(tasks=[_task("study", True)], assessment_id="a1")

        async def fake_get(user_id, aid):
            return _FakeAssessment("completed")
        monkeypatch.setattr(rma.assessment_history, "get", fake_get)
        asyncio.run(rma.assert_assessment_allows_completion(None, m, "u1"))  # no raise


# --------------------------------------------------------------------------- #
class TestEnrichment:
    def test_enrich_adds_optional_fields(self, monkeypatch):
        m = _mission(tasks=[_task("study", True), _task("practice", True)], assessment_id="a1")

        async def fake_get(user_id, aid):
            return _FakeAssessment("started")
        monkeypatch.setattr(rma.assessment_history, "get", fake_get)
        asyncio.run(rma.enrich_mission_assessment(None, m, "u1"))
        assert m["assessment_status"] == "started"
        assert m["assessment_available"] is True
        assert m["workflow_state"] == "assessment_in_progress"

    def test_enrich_safe_without_assessment(self):
        m = _mission(tasks=[_task("study", False)], assessment_id=None)
        asyncio.run(rma.enrich_mission_assessment(None, m, "u1"))
        assert m["assessment_status"] is None
        assert m["workflow_state"] == "mission_started"
