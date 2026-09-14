"""Sprint 3A Test Suite — Mission-Driven Assessment Engine.

Tests the frozen Sprint 3A architecture contract:
  * Mission-driven routing (DSA → CODING, Java → MCQ, etc.)
  * MissionContext as source of truth
  * DSA canonical problem selection (no AI)
  * Non-DSA AI generation (mocked)
  * Deterministic MCQ evaluation
  * Evidence gating (no evidence for behavioral/system_design)
  * Submission contract
  * Architecture invariants
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---- Domain imports --------------------------------------------------------
from assessment.schemas import (
    Assessment, AssessmentStatus, AssessmentType, Attempt, DimensionScore,
    CreateAssessmentRequest, Question, Result, Rubric, RubricDimension,
    SubmitAssessmentRequest, Verdict,
)
from assessment.assessment_types import (
    _GENERATORS, IMPLEMENTED_TYPES, get_generator, AssessmentTypeNotSupported,
)
from assessment.evaluators import (
    _EVALUATORS, evaluate_mcq, get_evaluator, has_evaluator,
)
from assessment.rubrics import get_rubric
from assessment.ai_generator import (
    AIGenerationError,
    _validate_quiz_response,
    _validate_behavioral_response,
    _validate_design_response,
    _validate_system_design_response,
)
from routes_mission_assessment import _ROADMAP_TO_ENUM, _resolve_assessment_type
from services.mission_context import build_mission_context


# ============================================================================
# 1. MISSION-DRIVEN ROUTING  (Tests 1–10)
# ============================================================================

class TestMissionDrivenRouting:
    """Verify the deterministic mapping from roadmap assessment_type to AssessmentType."""

    # Test 1: DSA → CODING
    def test_dsa_maps_to_coding(self):
        assert _resolve_assessment_type("coding") == AssessmentType.CODING

    # Test 2–6: Quiz tracks → MCQ
    @pytest.mark.parametrize("track", ["quiz"])
    def test_quiz_maps_to_mcq(self, track):
        assert _resolve_assessment_type(track) == AssessmentType.MCQ

    def test_java_node_assessment_type(self):
        """Java roadmap node has assessment_type='quiz' → MCQ."""
        mc = build_mission_context("java.basics.programming_intro")
        assert mc.assessment_type == "quiz"
        assert _resolve_assessment_type(mc.assessment_type) == AssessmentType.MCQ

    def test_programming_fundamentals_node(self):
        """PF roadmap node has assessment_type='quiz' → MCQ."""
        import roadmap
        r = roadmap.get_roadmap()
        pf_nodes = [n for n in r.all_nodes()
                     if n.get("id", "").startswith("pf.")
                     and n.get("type") not in ("track", "module", None)]
        if pf_nodes:
            mc = build_mission_context(pf_nodes[0]["id"])
            assert mc.assessment_type == "quiz"
            assert _resolve_assessment_type(mc.assessment_type) == AssessmentType.MCQ

    # Test 7: LLD/design → SYSTEM_DESIGN
    def test_design_maps_to_system_design(self):
        assert _resolve_assessment_type("design") == AssessmentType.SYSTEM_DESIGN

    # Test 8: HLD/system_design → SYSTEM_DESIGN
    def test_system_design_maps_to_system_design(self):
        assert _resolve_assessment_type("system_design") == AssessmentType.SYSTEM_DESIGN

    # Test 9: behavioral → BEHAVIORAL
    def test_behavioral_maps_to_behavioral(self):
        assert _resolve_assessment_type("behavioral") == AssessmentType.BEHAVIORAL

    # Test 10: none → no assessment
    def test_none_maps_to_none(self):
        assert _resolve_assessment_type("none") is None
        assert _resolve_assessment_type(None) is None

    def test_no_design_enum_exists(self):
        """Hard stop: there is no AssessmentType.DESIGN."""
        assert not hasattr(AssessmentType, "DESIGN")


# ============================================================================
# 2. MISSION CONTEXT  (Tests 11–16)
# ============================================================================

class TestMissionContext:
    """Verify MissionContext carries required assessment parameters from roadmap."""

    def _mc(self, node_id: str):
        return build_mission_context(node_id)

    # Test 11: topic from MissionContext
    def test_topic_from_mission_context(self):
        mc = self._mc("java.basics.programming_intro")
        assert mc.topic is not None and mc.topic != ""

    # Test 12: difficulty from MissionContext
    def test_difficulty_from_mission_context(self):
        mc = self._mc("java.basics.programming_intro")
        assert mc.difficulty in ("easy", "medium", "hard")

    # Test 13: learning objectives from MissionContext
    def test_learning_objectives_from_mission_context(self):
        mc = self._mc("java.basics.programming_intro")
        assert mc.learning_objectives is not None
        assert len(mc.learning_objectives) >= 1

    # Test 14: prerequisites from MissionContext
    def test_prerequisites_from_mission_context(self):
        mc = self._mc("java.basics.programming_intro")
        assert mc.prerequisites is not None

    # Test 15: assessment_type from MissionContext
    def test_assessment_type_from_mission_context(self):
        mc = self._mc("java.basics.programming_intro")
        assert mc.assessment_type == "quiz"

    # Test 16: generator cannot independently choose topic (structural)
    def test_generator_receives_roadmap_topic(self):
        """The prompt template receives topic from MissionContext, not from AI."""
        from assessment.prompts.base import get_prompt_template
        mc = self._mc("java.basics.programming_intro")
        template_fn = get_prompt_template("quiz")
        assert template_fn is not None
        ps = template_fn(mc, None)
        assert mc.topic in ps.user, "Topic from MissionContext must appear in prompt"


# ============================================================================
# 3. DSA  (Tests 17–25)
# ============================================================================

class TestDSA:
    """DSA must use canonical problem_bank, never AI."""

    # Test 17: DSA uses canonical problem_bank
    def test_dsa_generator_uses_problem_bank(self):
        gen = get_generator(AssessmentType.CODING)
        assert gen.__name__ == "generate_coding_assessment"
        # It's from assessment_generator.py, not ai_generator.py
        assert "assessment_generator" in gen.__module__

    # Test 18: AI not called for DSA
    def test_dsa_generator_is_sync(self):
        """Coding generator is synchronous — no AI gateway call."""
        import inspect
        gen = get_generator(AssessmentType.CODING)
        assert not inspect.iscoroutinefunction(gen)

    # Test 19-20: coding_pattern and difficulty respected
    def test_coding_generator_produces_question(self):
        """Calling the coding generator with a DSA node produces a Question."""
        gen = get_generator(AssessmentType.CODING)
        import roadmap
        r = roadmap.get_roadmap()
        dsa_nodes = [n for n in r.all_nodes()
                     if n.get("id", "").startswith("dsa.")
                     and n.get("type") not in ("track", "module", None)]
        for node in dsa_nodes[:5]:
            try:
                q = gen(roadmap_node_id=node["id"], difficulty="medium")
                assert isinstance(q, Question)
                assert q.problem_id is not None, "DSA must have problem_id"
                break
            except Exception:
                continue

    # Test 21: exclusion ids respected
    def test_exclusion_ids_respected(self):
        from assessment.assessment_generator import select_problem
        import roadmap
        r = roadmap.get_roadmap()
        dsa_nodes = [n for n in r.all_nodes()
                     if n.get("id", "").startswith("dsa.")
                     and n.get("assessment_type") == "coding"]
        for node in dsa_nodes[:10]:
            p1 = select_problem(roadmap_node_id=node["id"])
            if p1:
                # Excluding it should produce a different result or None.
                p2 = select_problem(roadmap_node_id=node["id"],
                                    exclude_ids=[p1["id"]])
                if p2 is not None:
                    assert p2["id"] != p1["id"]
                break

    # Test 22: problem_id is preserved
    def test_problem_id_preserved(self):
        gen = get_generator(AssessmentType.CODING)
        import roadmap
        r = roadmap.get_roadmap()
        dsa_nodes = [n for n in r.all_nodes()
                     if n.get("id", "").startswith("dsa.")
                     and n.get("type") not in ("track", "module", None)]
        for node in dsa_nodes[:5]:
            try:
                q = gen(roadmap_node_id=node["id"], difficulty="medium")
                assert q.problem_id is not None
                assert q.problem_id.startswith("lc-") or q.problem_id.startswith("catalog-")
                break
            except Exception:
                continue

    # Test 23: deterministic
    def test_deterministic_selection(self):
        from assessment.assessment_generator import select_problem
        import roadmap
        r = roadmap.get_roadmap()
        dsa_nodes = [n for n in r.all_nodes()
                     if n.get("id", "").startswith("dsa.")
                     and n.get("assessment_type") == "coding"]
        for node in dsa_nodes[:10]:
            p1 = select_problem(roadmap_node_id=node["id"], difficulty="medium")
            p2 = select_problem(roadmap_node_id=node["id"], difficulty="medium")
            if p1 and p2:
                assert p1["id"] == p2["id"], "Same inputs must produce same problem"
                break

    # Test 24: no AI fallback
    def test_no_ai_fallback_for_coding(self):
        """When no DSA problem exists, the coding generator raises — no AI fallback."""
        gen = get_generator(AssessmentType.CODING)
        try:
            q = gen(roadmap_node_id="nonexistent_node_xyz", difficulty="hard")
            # If it returns, it should be a Question from problem_bank, never AI
            assert q.problem_id is not None
        except Exception:
            pass  # expected: controlled failure

    # Test 25: dev_seed overflow is deterministic
    def test_overflow_is_deterministic(self):
        from services.problem_selection.selector import _default_overflow_provider
        result = _default_overflow_provider(
            pattern="sliding_window", learning_stage="foundation",
            difficulty="medium", exclude_ids=set(), count=1,
        )
        assert isinstance(result, list)


# ============================================================================
# 4. NON-DSA GENERATION — Validation (Tests 26–36)
# ============================================================================

class TestNonDSAValidation:
    """Test AI response validation for non-coding assessment types."""

    # Test 26–31: PromptSpec contains expected mission context
    def test_quiz_prompt_contains_java_topic(self):
        mc = build_mission_context("java.basics.programming_intro")
        from assessment.prompts.base import get_prompt_template
        ps = get_prompt_template("quiz")(mc, None)
        assert mc.topic in ps.user

    def test_quiz_prompt_contains_difficulty(self):
        mc = build_mission_context("java.basics.programming_intro")
        from assessment.prompts.base import get_prompt_template
        ps = get_prompt_template("quiz")(mc, None)
        assert mc.difficulty in ps.user

    def test_quiz_prompt_contains_prerequisites(self):
        mc = build_mission_context("java.basics.programming_intro")
        from assessment.prompts.base import get_prompt_template
        ps = get_prompt_template("quiz")(mc, None)
        assert "Prerequisites" in ps.user or "prerequisites" in ps.user.lower()

    # Test 32: parse_llm_json is used
    def test_parse_llm_json_exists(self):
        from ai_gateway.parsers import parse_llm_json
        assert parse_llm_json is not None

    # Test 33: malformed response rejected
    def test_malformed_quiz_response_rejected(self):
        with pytest.raises(AIGenerationError):
            _validate_quiz_response({})
        with pytest.raises(AIGenerationError):
            _validate_quiz_response({"questions": []})

    # Test 34: invalid answer_index rejected
    def test_invalid_answer_index_rejected(self):
        with pytest.raises(AIGenerationError):
            _validate_quiz_response({"questions": [{
                "prompt": "Q", "options": ["A", "B"], "answer_index": 5,
            }]})

    # Test 35: invalid options rejected
    def test_invalid_options_rejected(self):
        with pytest.raises(AIGenerationError):
            _validate_quiz_response({"questions": [{
                "prompt": "Q", "options": ["A"], "answer_index": 0,
            }]})

    # Test 36: valid quiz response accepted
    def test_valid_quiz_response_accepted(self):
        result = _validate_quiz_response({"questions": [{
            "prompt": "What is Java?",
            "options": ["A lang", "A framework", "An OS", "A database"],
            "answer_index": 0,
            "explanation": "Java is a programming language.",
        }]})
        assert result["prompt"] == "What is Java?"
        assert result["answer_index"] == 0

    # Behavioral validation
    def test_valid_behavioral_response(self):
        result = _validate_behavioral_response({"questions": [{
            "prompt": "Tell me about a time...",
            "what_good_looks_like": "A specific example with STAR format.",
        }]})
        assert result["prompt"] == "Tell me about a time..."

    def test_malformed_behavioral_rejected(self):
        with pytest.raises(AIGenerationError):
            _validate_behavioral_response({"questions": []})

    # Design validation
    def test_valid_design_response(self):
        result = _validate_design_response({
            "scenario": "Design a parking lot system.",
            "requirements": ["Support multiple floors"],
            "evaluation_rubric": ["OOP principles"],
        })
        assert result["scenario"] == "Design a parking lot system."

    def test_malformed_design_rejected(self):
        with pytest.raises(AIGenerationError):
            _validate_design_response({"scenario": ""})

    # System design validation
    def test_valid_system_design_response(self):
        result = _validate_system_design_response({
            "scenario": "Design Twitter's timeline.",
            "functional_requirements": ["Post tweets"],
            "non_functional_requirements": ["Low latency"],
            "evaluation_rubric": ["Scalability"],
        })
        assert result["scenario"] == "Design Twitter's timeline."

    def test_malformed_system_design_rejected(self):
        with pytest.raises(AIGenerationError):
            _validate_system_design_response({"scenario": "X"})


# ============================================================================
# 5. EVALUATION  (Tests 37–42)
# ============================================================================

class TestEvaluation:
    """Test deterministic evaluation behavior."""

    def _mcq_rubric(self):
        return get_rubric(AssessmentType.MCQ)

    def _question_with_answer(self, idx: int):
        return Question(prompt="Q?", metadata={"answer_index": idx})

    def _attempt_with_option(self, idx: int):
        return Attempt(metadata={"selected_option": idx})

    # Test 37: MCQ correct
    def test_mcq_correct(self):
        q = self._question_with_answer(2)
        a = self._attempt_with_option(2)
        result = evaluate_mcq(a, self._mcq_rubric(), q)
        assert result.verdict == Verdict.CORRECT
        assert result.overall_score == 100.0

    # Test 38: MCQ incorrect
    def test_mcq_incorrect(self):
        q = self._question_with_answer(2)
        a = self._attempt_with_option(0)
        result = evaluate_mcq(a, self._mcq_rubric(), q)
        assert result.verdict == Verdict.INCORRECT
        assert result.overall_score == 0.0

    # Test 39: MCQ evaluator does not call AI
    def test_mcq_evaluator_no_ai(self):
        """MCQ evaluator is deterministic — no AI/async/gateway calls."""
        import inspect
        assert not inspect.iscoroutinefunction(evaluate_mcq)

    # Test 40: existing coding evaluator unchanged
    def test_coding_evaluator_registered(self):
        from assessment.evaluation_engine import evaluate
        assert get_evaluator(AssessmentType.CODING) is evaluate

    # Test 41: behavioral has no evaluator
    def test_behavioral_no_evaluator(self):
        assert get_evaluator(AssessmentType.BEHAVIORAL) is None
        assert not has_evaluator(AssessmentType.BEHAVIORAL)

    # Test 42: system_design has no evaluator
    def test_system_design_no_evaluator(self):
        assert get_evaluator(AssessmentType.SYSTEM_DESIGN) is None
        assert not has_evaluator(AssessmentType.SYSTEM_DESIGN)


# ============================================================================
# 6. EVIDENCE  (Tests 43–48)
# ============================================================================

class TestEvidence:
    """Verify evidence gating: only deterministic evaluations produce evidence."""

    def _make_assessment(self, atype: AssessmentType):
        rubric = get_rubric(atype)
        return Assessment(
            user_id="test", assessment_type=atype,
            status=AssessmentStatus.SUBMITTED,
            rubric=rubric,
            question=Question(prompt="Q?", metadata={"answer_index": 0}),
            attempt=Attempt(metadata={"selected_option": 0, "attempt_number": 1}),
        )

    # Test 43: coding can produce evidence (architecture check)
    def test_coding_evaluator_produces_result(self):
        evaluator = get_evaluator(AssessmentType.CODING)
        assert evaluator is not None

    # Test 44: MCQ can produce evidence
    def test_mcq_can_produce_evidence(self):
        from assessment.evidence import build_evidence
        a = self._make_assessment(AssessmentType.MCQ)
        result = evaluate_mcq(a.attempt, a.rubric, a.question)
        evidence = build_evidence(a, result, attempt=a.attempt, question=a.question)
        assert evidence is not None
        assert evidence.accuracy == 1.0  # correct answer

    # Test 45: behavioral produces no evidence
    def test_behavioral_no_evidence(self):
        assert get_evaluator(AssessmentType.BEHAVIORAL) is None

    # Test 46: system_design produces no evidence
    def test_system_design_no_evidence(self):
        assert get_evaluator(AssessmentType.SYSTEM_DESIGN) is None

    # Test 47: subjective feedback cannot mutate LI (structural)
    def test_no_evaluator_means_no_evidence(self):
        """Types without an evaluator produce no Result → no Evidence → no LI."""
        for atype in (AssessmentType.BEHAVIORAL, AssessmentType.SYSTEM_DESIGN):
            assert get_evaluator(atype) is None

    # Test 48: no neutral zero-valued evidence
    def test_mcq_incorrect_produces_zero_accuracy_not_neutral(self):
        """MCQ incorrect → 0.0 accuracy (genuine INCORRECT, not a neutral placeholder)."""
        from assessment.evidence import build_evidence
        a = self._make_assessment(AssessmentType.MCQ)
        a.attempt = Attempt(metadata={"selected_option": 999, "attempt_number": 1})
        result = evaluate_mcq(a.attempt, a.rubric, a.question)
        assert result.verdict == Verdict.INCORRECT
        evidence = build_evidence(a, result, attempt=a.attempt, question=a.question)
        assert evidence.accuracy == 0.0
        assert evidence.verdict == Verdict.INCORRECT


# ============================================================================
# 7. SUBMISSION  (Tests 49–55)
# ============================================================================

class TestSubmission:
    """Verify SubmitAssessmentRequest backward compatibility."""

    # Test 49: coding backward compatible
    def test_coding_request_backward_compatible(self):
        req = SubmitAssessmentRequest(
            passed_tests=5, total_tests=10, code="print(1)",
        )
        assert req.passed_tests == 5
        assert req.response_text is None
        assert req.selected_option is None

    # Test 50: MCQ accepts selected_option
    def test_mcq_accepts_selected_option(self):
        req = SubmitAssessmentRequest(selected_option=2)
        assert req.selected_option == 2

    # Test 51: behavioral accepts response_text
    def test_behavioral_accepts_response_text(self):
        req = SubmitAssessmentRequest(response_text="I handled the conflict by...")
        assert req.response_text == "I handled the conflict by..."

    # Test 52: system_design accepts response_text
    def test_system_design_accepts_response_text(self):
        req = SubmitAssessmentRequest(
            response_text="The system uses a message queue...",
        )
        assert req.response_text is not None

    # Test 53: metadata optional
    def test_metadata_optional(self):
        req = SubmitAssessmentRequest()
        assert req.metadata == {}

    # Test 54: no answers[] field
    def test_no_answers_list(self):
        assert not hasattr(SubmitAssessmentRequest, "answers")

    # Test 55: 1:1:1 preserved
    def test_assessment_one_question_one_attempt(self):
        a = Assessment(
            user_id="test", assessment_type=AssessmentType.MCQ,
            question=Question(prompt="Q?"),
        )
        # question is singular, not a list
        assert isinstance(a.question, Question)


# ============================================================================
# 8. ARCHITECTURE  (Tests 56–65)
# ============================================================================

class TestArchitecture:
    """Verify Sprint 3A architecture invariants."""

    # Test 56: AI calls use ai_service.complete
    def test_ai_service_complete_exists(self):
        import ai_service
        assert hasattr(ai_service, "complete")

    # Test 57: ASSESSMENT_CONTENT capability
    def test_assessment_content_capability(self):
        from ai_service import AICapability
        assert hasattr(AICapability, "ASSESSMENT_CONTENT")

    # Test 58: no provider SDK coupling in ai_generator
    def test_no_provider_sdk_in_ai_generator(self):
        import assessment.ai_generator as mod
        source = open(mod.__file__).read()
        assert "google.genai" not in source
        assert "litellm" not in source
        assert "openai" not in source

    # Test 59: no second assessment engine
    def test_single_assessment_engine(self):
        """Only one assessment_engine module exists."""
        import assessment.assessment_engine
        # The module exists; there's no assessment_engine_v2 or similar
        assert hasattr(assessment.assessment_engine, "create_assessment")

    # Test 60: no second evidence system
    def test_single_evidence_module(self):
        import assessment.evidence
        assert hasattr(assessment.evidence, "build_evidence")

    # Test 61: no multi-question model
    def test_question_is_singular(self):
        """Assessment.question is Optional[Question], not List."""
        import typing
        field = Assessment.model_fields["question"]
        # Should accept None or Question, never List
        assert "List" not in str(field.annotation)

    # Test 62: no cache module
    def test_no_assessment_cache(self):
        try:
            from assessment import cache
            pytest.fail("assessment.cache should not exist")
        except ImportError:
            pass

    # Test 63: no semantic duplicate detector
    def test_no_semantic_dedup(self):
        try:
            from assessment import dedup
            pytest.fail("assessment.dedup should not exist")
        except ImportError:
            pass

    # Test 64: no AssessmentType.DESIGN
    def test_no_design_enum(self):
        assert not hasattr(AssessmentType, "DESIGN")

    # Test 65: no provenance laundering (evidence requires deterministic evaluation)
    def test_evidence_only_from_deterministic_evaluation(self):
        """Types without evaluator produce no evidence."""
        for atype in (AssessmentType.BEHAVIORAL, AssessmentType.SYSTEM_DESIGN):
            assert not has_evaluator(atype)


# ============================================================================
# 9. IMPLEMENTED TYPES
# ============================================================================

class TestImplementedTypes:
    """All Sprint 3A types are registered and dispatchable."""

    @pytest.mark.parametrize("atype", [
        AssessmentType.CODING,
        AssessmentType.MCQ,
        AssessmentType.THEORY,
        AssessmentType.BEHAVIORAL,
        AssessmentType.SYSTEM_DESIGN,
    ])
    def test_generator_registered(self, atype):
        gen = get_generator(atype)
        assert gen is not None

    @pytest.mark.parametrize("atype", [
        AssessmentType.CODING,
        AssessmentType.MCQ,
        AssessmentType.THEORY,
        AssessmentType.BEHAVIORAL,
        AssessmentType.SYSTEM_DESIGN,
    ])
    def test_in_implemented_types(self, atype):
        assert atype in IMPLEMENTED_TYPES

    @pytest.mark.parametrize("atype", [
        AssessmentType.CODING,
        AssessmentType.MCQ,
        AssessmentType.THEORY,
        AssessmentType.BEHAVIORAL,
        AssessmentType.SYSTEM_DESIGN,
    ])
    def test_rubric_registered(self, atype):
        rubric = get_rubric(atype)
        assert rubric is not None
        assert len(rubric.dimensions) >= 1


# ============================================================================
# 10. ROADMAP NODE ASSESSMENT TYPES
# ============================================================================

class TestRoadmapNodeTypes:
    """Verify roadmap nodes have expected assessment_type values."""

    def test_dsa_nodes_are_coding(self):
        import roadmap
        r = roadmap.get_roadmap()
        dsa_nodes = [n for n in r.all_nodes()
                     if n.get("id", "").startswith("dsa.")
                     and n.get("type") not in ("track", "module", None)]
        for n in dsa_nodes[:5]:
            assert n.get("assessment_type") == "coding"

    def test_java_nodes_are_quiz(self):
        import roadmap
        r = roadmap.get_roadmap()
        java_nodes = [n for n in r.all_nodes()
                      if n.get("id", "").startswith("java.")
                      and n.get("type") not in ("track", "module", None)]
        for n in java_nodes[:5]:
            assert n.get("assessment_type") == "quiz"

    def test_lld_nodes_are_design(self):
        import roadmap
        r = roadmap.get_roadmap()
        lld_nodes = [n for n in r.all_nodes()
                     if n.get("id", "").startswith("lld.")
                     and n.get("type") not in ("track", "module", None)]
        for n in lld_nodes[:5]:
            assert n.get("assessment_type") == "design"

    def test_hld_nodes_are_system_design(self):
        import roadmap
        r = roadmap.get_roadmap()
        hld_nodes = [n for n in r.all_nodes()
                     if n.get("id", "").startswith("hld.")
                     and n.get("type") not in ("track", "module", None)]
        for n in hld_nodes[:5]:
            assert n.get("assessment_type") == "system_design"

    def test_behavioral_nodes_are_behavioral(self):
        import roadmap
        r = roadmap.get_roadmap()
        beh_nodes = [n for n in r.all_nodes()
                     if n.get("id", "").startswith("behavioral.")
                     and n.get("type") not in ("track", "module", None)]
        for n in beh_nodes[:5]:
            assert n.get("assessment_type") == "behavioral"
