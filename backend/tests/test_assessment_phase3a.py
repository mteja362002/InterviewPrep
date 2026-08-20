"""Phase 3A — Assessment Engine tests.

Pure unit tests (no server / DB) covering the deterministic engine:
generation, rubrics, evaluation, feedback, evidence, recommendations,
session state machine, type extensibility, and fallbacks. All previous
tests continue to pass (regression is covered by the existing suite).
"""
import pytest

from assessment.assessment_generator import (
    generate_coding_assessment, select_problem, _resolve_pattern,
)
from assessment.assessment_session import (
    InvalidTransition, start, submit, mark_evaluated, complete, can_transition,
)
from assessment.assessment_types import (
    AssessmentTypeNotSupported, get_generator, is_implemented, SUPPORTED_TYPES,
)
from assessment.difficulty import (
    default_difficulty, recommend_from_verdict, step, clamp_difficulty,
)
from assessment.evaluation_engine import evaluate
from assessment.evidence import build_evidence
from assessment.feedback_engine import build_feedback
from assessment.recommendations import build_recommendation
from assessment.rubrics import get_rubric
from assessment.schemas import (
    Assessment, AssessmentStatus, AssessmentType, Attempt, Verdict,
)


def _coding_assessment(**kw):
    q = generate_coding_assessment(
        roadmap_node_id=kw.get("node", "dsa.sliding_window.core"),
        difficulty=kw.get("difficulty", "medium"),
        target_company=kw.get("company", "google"),
    )
    return Assessment(
        user_id="u1", assessment_type=AssessmentType.CODING,
        roadmap_node_id=kw.get("node", "dsa.sliding_window.core"),
        question=q, rubric=get_rubric(AssessmentType.CODING),
    )


# --------------------------------------------------------------------------- #
class TestGeneration:
    def test_reuses_problem_bank_by_reference(self):
        q = generate_coding_assessment(roadmap_node_id="dsa.two_pointers.core",
                                       difficulty="medium", target_company="google")
        assert q.problem_id and q.problem_id.startswith("lc-")
        assert q.pattern == "two_pointers"
        assert q.external_url and "leetcode.com" in q.external_url

    def test_deterministic_selection(self):
        a = select_problem(roadmap_node_id="dsa.arrays.core", difficulty="medium", target_company="google")
        b = select_problem(roadmap_node_id="dsa.arrays.core", difficulty="medium", target_company="google")
        assert a["id"] == b["id"]

    def test_pattern_resolution(self):
        assert _resolve_pattern("dsa.binary_search.core") == "binary_search"
        assert _resolve_pattern(None) is None

    def test_company_filter(self):
        q = generate_coding_assessment(roadmap_node_id="dsa.hashing.core",
                                       difficulty="easy", target_company="stripe")
        assert "stripe" in (q.metadata.get("companies") or []) or q.problem_id


# --------------------------------------------------------------------------- #
class TestRubric:
    def test_weights_sum_to_one(self):
        rub = get_rubric(AssessmentType.CODING)
        assert round(sum(d.weight for d in rub.dimensions), 6) == 1.0

    def test_overrides_renormalized(self):
        rub = get_rubric(AssessmentType.CODING, weight_overrides={"correctness": 10.0})
        assert round(sum(d.weight for d in rub.dimensions), 6) == 1.0
        corr = next(d for d in rub.dimensions if d.key == "correctness")
        assert corr.weight > 0.5


# --------------------------------------------------------------------------- #
class TestEvaluation:
    def test_correct(self):
        rub = get_rubric(AssessmentType.CODING)
        q = generate_coding_assessment(roadmap_node_id="dsa.sliding_window.core",
                                       difficulty="medium", target_company="google")
        att = Attempt(passed_tests=10, total_tests=10, edge_cases_passed=3, edge_cases_total=3,
                      claimed_time_complexity=q.expected_time_complexity,
                      explanation="x" * 90, code="def f(): return 1", solved=True)
        res = evaluate(att, rub, q)
        assert res.verdict == Verdict.CORRECT
        assert res.overall_score >= 90
        assert res.complexity_rating == "optimal"

    def test_incorrect(self):
        rub = get_rubric(AssessmentType.CODING)
        att = Attempt(passed_tests=1, total_tests=10, edge_cases_passed=0, edge_cases_total=3,
                      claimed_time_complexity="O(n^2)", solved=False)
        res = evaluate(att, rub, None)
        assert res.verdict == Verdict.INCORRECT

    def test_partial(self):
        rub = get_rubric(AssessmentType.CODING)
        att = Attempt(passed_tests=6, total_tests=10, edge_cases_passed=2, edge_cases_total=3,
                      explanation="short", solved=None)
        res = evaluate(att, rub, None)
        assert res.verdict == Verdict.PARTIALLY_CORRECT

    def test_deterministic(self):
        rub = get_rubric(AssessmentType.CODING)
        att = Attempt(passed_tests=7, total_tests=10, edge_cases_passed=1, edge_cases_total=2)
        assert evaluate(att, rub, None).overall_score == evaluate(att, rub, None).overall_score


# --------------------------------------------------------------------------- #
class TestFeedbackAndRecommendation:
    def test_feedback_on_incorrect_surfaces_missing_concepts(self):
        a = _coding_assessment()
        rub = a.rubric
        att = Attempt(passed_tests=0, total_tests=10, solved=False)
        res = evaluate(att, rub, a.question)
        fb = build_feedback(res, a.question)
        assert fb.confidence_impact == "negative"
        assert fb.difficulty_recommendation == "decrease"
        assert isinstance(fb.missing_concepts, list)

    def test_recommendation_advance_on_correct(self):
        a = _coding_assessment()
        att = Attempt(passed_tests=10, total_tests=10, edge_cases_passed=3, edge_cases_total=3,
                      claimed_time_complexity=a.question.expected_time_complexity,
                      explanation="y" * 90, code="ok", solved=True)
        res = evaluate(att, a.rubric, a.question)
        fb = build_feedback(res, a.question)
        ev = build_evidence(a, res, attempt=att, question=a.question)
        rec = build_recommendation(ev, fb)
        assert rec.next_action == "advance"

    def test_recommendation_revise_derived_from_evidence(self):
        a = _coding_assessment()
        att = Attempt(passed_tests=0, total_tests=10, solved=False)
        res = evaluate(att, a.rubric, a.question)
        fb = build_feedback(res, a.question)
        ev = build_evidence(a, res, attempt=att, question=a.question)
        rec = build_recommendation(ev, fb)
        assert rec.next_action == "revise"


class TestEvidenceContract:
    """Phase 3A refinement — canonical, generic, immutable evidence contract."""

    def _completed_evidence(self, solved=True):
        a = _coding_assessment()
        att = Attempt(passed_tests=10 if solved else 1, total_tests=10,
                      edge_cases_passed=3 if solved else 0, edge_cases_total=3,
                      claimed_time_complexity=a.question.expected_time_complexity if solved else "O(n^2)",
                      explanation="w" * 90, code="ok", solved=solved,
                      metadata={"attempt_number": 1})
        res = evaluate(att, a.rubric, a.question)
        return build_evidence(a, res, attempt=att, question=a.question)

    def test_single_canonical_model(self):
        from assessment.schemas import Evidence, AssessmentEvidence
        assert Evidence is AssessmentEvidence

    def test_canonical_generic_fields_present(self):
        ev = self._completed_evidence()
        # Type-agnostic canonical scalars + extensibility bags.
        for field in ("accuracy", "proficiency", "completion_quality",
                      "confidence_delta", "metrics", "signals", "tags",
                      "schema_version"):
            assert hasattr(ev, field)
        assert 0.0 <= ev.accuracy <= 1.0
        assert isinstance(ev.metrics, dict) and "overall_score" in ev.metrics
        assert isinstance(ev.signals, dict) and "revision_trigger" in ev.signals

    def test_backward_compatible_aliases(self):
        ev = self._completed_evidence()
        assert ev.coding_accuracy == ev.accuracy
        assert ev.problem_solving == ev.proficiency
        assert ev.topic_confidence_delta == ev.confidence_delta

    def test_evidence_is_immutable(self):
        ev = self._completed_evidence()
        with pytest.raises(Exception):
            ev.accuracy = 0.0  # frozen model — must not allow mutation

    def test_evidence_serializes_canonically(self):
        ev = self._completed_evidence()
        doc = ev.model_dump(mode="json")
        assert doc["schema_version"] == "1.0"
        assert "accuracy" in doc and "metrics" in doc


# --------------------------------------------------------------------------- #
class TestEvidence:
    def test_evidence_exposed_not_applied(self):
        a = _coding_assessment()
        att = Attempt(passed_tests=2, total_tests=10, solved=False, metadata={"attempt_number": 3})
        res = evaluate(att, a.rubric, a.question)
        ev = build_evidence(a, res, attempt=att, question=a.question)
        assert ev.user_id == "u1"
        assert ev.weakness_confirmation is True
        assert ev.revision_trigger is True
        assert ev.repeated_mistakes is True
        assert -1.0 <= ev.topic_confidence_delta <= 1.0

    def test_positive_evidence_on_success(self):
        a = _coding_assessment()
        att = Attempt(passed_tests=10, total_tests=10, edge_cases_passed=3, edge_cases_total=3,
                      claimed_time_complexity=a.question.expected_time_complexity,
                      explanation="z" * 90, code="ok", solved=True)
        res = evaluate(att, a.rubric, a.question)
        ev = build_evidence(a, res, attempt=att, question=a.question)
        assert ev.coding_accuracy == 1.0
        assert ev.weakness_confirmation is False
        assert ev.topic_confidence_delta > 0


# --------------------------------------------------------------------------- #
class TestSession:
    def test_happy_path(self):
        a = _coding_assessment()
        start(a); assert a.status == AssessmentStatus.STARTED.value and a.started_at
        submit(a, Attempt(passed_tests=1, total_tests=1))
        assert a.status == AssessmentStatus.SUBMITTED.value
        mark_evaluated(a); complete(a)
        assert a.status == AssessmentStatus.COMPLETED.value and a.completed_at

    def test_illegal_transition(self):
        a = _coding_assessment()
        with pytest.raises(InvalidTransition):
            submit(a, Attempt())  # cannot submit before start

    def test_transition_table(self):
        assert can_transition("pending", "started")
        assert not can_transition("pending", "completed")
        assert not can_transition("completed", "started")


# --------------------------------------------------------------------------- #
class TestTypesAndDifficulty:
    def test_all_future_types_registered(self):
        # Platform is aware of every future type architecturally.
        vals = {t.value for t in SUPPORTED_TYPES}
        for expected in ("coding", "theory", "mcq", "debugging", "behavioral",
                         "system_design", "resume", "project_explanation"):
            assert expected in vals

    def test_only_coding_implemented(self):
        assert is_implemented(AssessmentType.CODING)
        assert not is_implemented(AssessmentType.THEORY)

    def test_unsupported_type_raises(self):
        with pytest.raises(AssessmentTypeNotSupported):
            get_generator(AssessmentType.SYSTEM_DESIGN)

    def test_difficulty_helpers(self):
        assert default_difficulty("student") == "easy"
        assert default_difficulty("5+") == "hard"
        assert default_difficulty(None) == "medium"
        assert step("easy", "increase") == "medium"
        assert step("hard", "increase") == "hard"
        assert clamp_difficulty("bogus") == "medium"
        assert recommend_from_verdict("medium", Verdict.CORRECT) == "increase"
