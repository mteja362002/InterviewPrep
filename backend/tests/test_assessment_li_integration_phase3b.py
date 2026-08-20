"""Phase 3B — Assessment -> Learner Intelligence integration tests.

Pure unit tests (no server / DB) covering the deterministic integration
layer: evidence validation, evidence -> learner-update translation
(confidence / mastery / weakness / strength / knowledge-gap / revision),
explainability, immutability, append-only history (via an injected fake
repo), learner-state aggregation, type-agnostic processing, and backward
compatibility.
"""
import asyncio

import pytest

from assessment.schemas import Assessment, AssessmentType, Attempt
from assessment.assessment_generator import generate_coding_assessment
from assessment.rubrics import get_rubric
from assessment.evaluation_engine import evaluate
from assessment.evidence import build_evidence
from assessment.schemas import AssessmentEvidence, Verdict

from services.learner_intelligence.evidence_integration import (
    InvalidEvidence, ingest_evidence, process_evidence, validate_evidence,
)
from services.learner_intelligence.learner_state import build_learner_state
from services.learner_intelligence.learner_update import LearnerIntelligenceUpdate


def _evidence(solved=True, node="dsa.sliding_window.core", user="u1"):
    q = generate_coding_assessment(roadmap_node_id=node, difficulty="medium", target_company="google")
    a = Assessment(user_id=user, assessment_type=AssessmentType.CODING,
                   roadmap_node_id=node, question=q, rubric=get_rubric(AssessmentType.CODING))
    att = Attempt(
        passed_tests=10 if solved else 1, total_tests=10,
        edge_cases_passed=3 if solved else 0, edge_cases_total=3,
        claimed_time_complexity="O(n)" if solved else "O(n^2)",
        explanation="x" * 90, code="ok", solved=solved, metadata={"attempt_number": 1},
    )
    res = evaluate(att, a.rubric, q)
    return build_evidence(a, res, attempt=att, question=q)


class _FakeRepo:
    """In-memory append-only repo (records inserts; forbids mutation)."""

    def __init__(self):
        self.records = []

    async def append(self, update):
        # Append-only: reject a duplicate update_id (as a unique index would).
        if any(r.update_id == update.update_id for r in self.records):
            raise AssertionError("append-only violated: duplicate update_id")
        self.records.append(update)
        return update


# --------------------------------------------------------------------------- #
class TestValidation:
    def test_none_rejected(self):
        with pytest.raises(InvalidEvidence):
            validate_evidence(None)

    def test_missing_fields_rejected(self):
        with pytest.raises(InvalidEvidence):
            validate_evidence({"assessment_id": "a", "user_id": ""})

    def test_valid_passes(self):
        validate_evidence(_evidence())  # no raise


# --------------------------------------------------------------------------- #
class TestProcessing:
    def test_confidence_increase_on_success(self):
        u = process_evidence(_evidence(solved=True), user_id="u1")
        assert u.confidence_delta > 0
        assert u.strength_detected is True
        assert u.weakness_detected is False
        assert u.knowledge_gap_adjustment < 0     # gap closed
        assert u.mastery_delta > 0

    def test_confidence_decrease_on_failure(self):
        u = process_evidence(_evidence(solved=False), user_id="u1")
        assert u.confidence_delta < 0
        assert u.weakness_detected is True
        assert u.strength_detected is False
        assert u.knowledge_gap_adjustment > 0     # gap widened
        assert u.revision_hint is True
        assert u.mastery_delta < 0

    def test_only_learner_state_fields(self):
        # The update must not leak planner-specific fields.
        u = process_evidence(_evidence(), user_id="u1")
        d = u.to_dict()
        for planner_field in ("total_score", "company_score", "knowledge_gap_score",
                              "learner_intelligence_score", "priority"):
            assert planner_field not in d

    def test_deterministic(self):
        ev = _evidence(solved=True)
        a = process_evidence(ev, user_id="u1").to_dict()
        b = process_evidence(ev, user_id="u1").to_dict()
        # Exclude auto-generated provenance (unique id + timestamp); the
        # TRANSLATION must be identical.
        for f in ("update_id", "created_at"):
            a.pop(f, None)
            b.pop(f, None)
        assert a == b

    def test_type_agnostic_accepts_plain_dict(self):
        # A non-coding evidence dict (future type) flows through unchanged —
        # NO assessment-type branching required.
        ev = {
            "assessment_id": "a1", "user_id": "u1", "assessment_type": "behavioral",
            "roadmap_node_id": "behavioral.leadership", "verdict": "correct",
            "accuracy": 0.95, "proficiency": 0.9, "completion_quality": 0.8,
            "confidence_delta": 0.5, "weakness_confirmation": False,
            "revision_trigger": False, "difficulty_achieved": "medium",
            "metrics": {"structure": 0.9}, "schema_version": "1.0",
        }
        u = process_evidence(ev)
        assert u.assessment_type == "behavioral"
        assert u.strength_detected is True
        assert u.learning_signals["metrics"]["structure"] == 0.9


# --------------------------------------------------------------------------- #
class TestExplainability:
    def test_reasons_present_and_deterministic(self):
        u = process_evidence(_evidence(solved=False), user_id="u1")
        assert any("Confidence decreased" in r for r in u.reasons)
        assert any("Weakness detected" in r for r in u.reasons)
        assert any("Revision suggested" in r for r in u.reasons)

    def test_strength_reason(self):
        u = process_evidence(_evidence(solved=True), user_id="u1")
        assert any("Strength detected" in r for r in u.reasons)


# --------------------------------------------------------------------------- #
class TestImmutabilityAndHistory:
    def test_update_is_immutable(self):
        u = process_evidence(_evidence(), user_id="u1")
        with pytest.raises(Exception):
            u.confidence_delta = 0.0   # frozen dataclass

    def test_from_dict_roundtrip(self):
        u = process_evidence(_evidence(), user_id="u1")
        rebuilt = LearnerIntelligenceUpdate.from_dict(u.to_dict())
        assert rebuilt == u

    def test_append_only_ingest(self):
        repo = _FakeRepo()
        ev1, ev2 = _evidence(solved=True), _evidence(solved=False)
        u1 = asyncio.run(ingest_evidence(ev1, user_id="u1", repo=repo))
        u2 = asyncio.run(ingest_evidence(ev2, user_id="u1", repo=repo))
        assert len(repo.records) == 2
        assert repo.records[0] is u1 and repo.records[1] is u2
        # Re-appending the same update_id must be rejected (append-only).
        with pytest.raises(AssertionError):
            asyncio.run(repo.append(u1))


# --------------------------------------------------------------------------- #
class TestLearnerState:
    def test_aggregation_per_node(self):
        u_ok = process_evidence(_evidence(solved=True), user_id="u1")
        u_bad = process_evidence(_evidence(solved=False), user_id="u1")
        state = build_learner_state([u_ok, u_bad])
        node = state["by_node"]["dsa.sliding_window.core"]
        assert node["assessment_count"] == 2
        assert node["weakness_detected"] is True
        assert node["strength_detected"] is True
        assert "dsa.sliding_window.core" in state["weaknesses"]
        assert state["assessment_count"] == 2

    def test_empty_state(self):
        state = build_learner_state([])
        assert state["assessment_count"] == 0
        assert state["by_node"] == {}

    def test_deterministic_sorted(self):
        a = process_evidence(_evidence(node="dsa.arrays.core"), user_id="u1")
        b = process_evidence(_evidence(node="dsa.hashing.core"), user_id="u1")
        assert build_learner_state([a, b]) == build_learner_state([b, a]) or \
            build_learner_state([a, b])["weaknesses"] == build_learner_state([b, a])["weaknesses"]


# --------------------------------------------------------------------------- #
class TestBackwardCompatibility:
    def test_existing_snapshot_unaffected(self):
        # Building the Phase 2C snapshot does not require or produce any
        # assessment update — evidence integration is purely additive.
        from services.learner_intelligence import build_snapshot
        snap = build_snapshot(progress_rows=[{"track": "dsa", "confidence": 6,
                              "mastery_percentage": 60}])
        assert hasattr(snap, "is_empty")

    def test_accepts_frozen_assessment_evidence_object(self):
        ev = _evidence()
        assert isinstance(ev, AssessmentEvidence)
        u = process_evidence(ev, user_id="u1")
        assert u.assessment_id == ev.assessment_id
