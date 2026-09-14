"""Non-coding AI Assessment Generator — Mission-driven content generation.

Sprint 3A: generates questions for MCQ, THEORY, BEHAVIORAL, and SYSTEM_DESIGN
assessment types through the existing AI Gateway.

Invariants:
  * MissionContext (from the roadmap node) is the SOLE source of topic,
    difficulty, prerequisites, learning objectives.
  * The AI generates content WITHIN the deterministic scope — it never
    independently chooses a topic, difficulty, or prerequisite.
  * All AI calls go through ``ai_service.complete()`` with capability
    ``ASSESSMENT_CONTENT``.
  * No provider SDK is imported or called directly.
  * Coding assessments do NOT use this generator — they use the canonical
    problem_bank via assessment_generator.py.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from ai_gateway.parsers import parse_llm_json
from services.mission_context import build_mission_context

from .assessment_types import register_generator
from .prompts.base import get_prompt_template
from .schemas import AssessmentType, Question

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Validation helpers — deterministic, no LLM calls
# --------------------------------------------------------------------------- #

class AIGenerationError(Exception):
    """Raised when AI generation fails validation."""


def _validate_quiz_response(parsed: dict) -> dict:
    """Validate a quiz AI response and return the first valid question."""
    questions = parsed.get("questions")
    if not questions or not isinstance(questions, list):
        raise AIGenerationError("AI response missing 'questions' array.")

    for q in questions:
        prompt = (q.get("prompt") or "").strip()
        options = q.get("options")
        answer_index = q.get("answer_index")
        explanation = q.get("explanation") or ""

        if not prompt:
            continue
        if not options or not isinstance(options, list) or len(options) < 2:
            continue
        if answer_index is None:
            continue
        try:
            idx = int(answer_index)
        except (TypeError, ValueError):
            continue
        if idx < 0 or idx >= len(options):
            continue

        return {
            "prompt": prompt,
            "options": options,
            "answer_index": idx,
            "explanation": explanation.strip(),
        }

    raise AIGenerationError("No valid quiz question found in AI response.")


def _validate_behavioral_response(parsed: dict) -> dict:
    """Validate a behavioral AI response and return the first valid question."""
    questions = parsed.get("questions")
    if not questions or not isinstance(questions, list):
        raise AIGenerationError("AI response missing 'questions' array.")

    for q in questions:
        prompt = (q.get("prompt") or "").strip()
        guidance = (q.get("what_good_looks_like") or "").strip()

        if not prompt:
            continue
        if not guidance:
            continue

        return {
            "prompt": prompt,
            "what_good_looks_like": guidance,
        }

    raise AIGenerationError("No valid behavioral question found in AI response.")


def _validate_design_response(parsed: dict) -> dict:
    """Validate a design (LLD) AI response."""
    scenario = (parsed.get("scenario") or "").strip()
    requirements = parsed.get("requirements")
    rubric = parsed.get("evaluation_rubric") or []

    if not scenario:
        raise AIGenerationError("AI response missing 'scenario'.")
    if not requirements or not isinstance(requirements, list) or len(requirements) < 1:
        raise AIGenerationError("AI response missing valid 'requirements'.")

    return {
        "scenario": scenario,
        "requirements": requirements,
        "evaluation_rubric": rubric,
    }


def _validate_system_design_response(parsed: dict) -> dict:
    """Validate a system_design (HLD) AI response."""
    scenario = (parsed.get("scenario") or "").strip()
    func_reqs = parsed.get("functional_requirements")
    nf_reqs = parsed.get("non_functional_requirements")
    rubric = parsed.get("evaluation_rubric") or []

    if not scenario:
        raise AIGenerationError("AI response missing 'scenario'.")
    if not func_reqs or not isinstance(func_reqs, list) or len(func_reqs) < 1:
        raise AIGenerationError("AI response missing valid 'functional_requirements'.")
    if not nf_reqs or not isinstance(nf_reqs, list) or len(nf_reqs) < 1:
        raise AIGenerationError("AI response missing valid 'non_functional_requirements'.")

    return {
        "scenario": scenario,
        "functional_requirements": func_reqs,
        "non_functional_requirements": nf_reqs,
        "evaluation_rubric": rubric,
    }


# --------------------------------------------------------------------------- #
# Generator functions — one per assessment type
# --------------------------------------------------------------------------- #

async def _generate_via_ai(
    *,
    roadmap_node_id: Optional[str],
    prompt_template_key: str,
    validate_fn,
    build_question_fn,
    target_company: Optional[str] = None,
    learner_signals: Optional[dict] = None,
    **_ignored,
) -> Question:
    """Common AI generation pipeline: MissionContext → PromptSpec → AI → validate → Question."""
    import ai_service
    from ai_service import AICapability

    # Build MissionContext from the roadmap node — deterministic.
    if not roadmap_node_id:
        raise AIGenerationError("No roadmap_node_id provided for AI assessment generation.")

    mc = build_mission_context(roadmap_node_id)

    # Inject target company into MissionContext if provided by the learner.
    if target_company:
        mc.target_companies = list(mc.target_companies or [])
        if target_company not in mc.target_companies:
            mc.target_companies.insert(0, target_company)

    # Get the prompt template — deterministic registry lookup.
    template_fn = get_prompt_template(prompt_template_key)
    if template_fn is None:
        raise AIGenerationError(
            f"No prompt template registered for '{prompt_template_key}'."
        )

    prompt_spec = template_fn(mc, learner_signals)

    # Call AI through the gateway — the ONLY AI boundary.
    raw = await ai_service.complete(
        capability=AICapability.ASSESSMENT_CONTENT,
        system_message=prompt_spec.system,
        prompt=prompt_spec.user,
    )

    # Parse and validate — deterministic.
    parsed = parse_llm_json(raw)
    if parsed is None:
        raise AIGenerationError("AI response could not be parsed as JSON.")

    validated = validate_fn(parsed)
    return build_question_fn(validated, mc)


def _build_quiz_question(validated: dict, mc) -> Question:
    """Build a Question from validated quiz data."""
    return Question(
        prompt=validated["prompt"],
        metadata={
            "type": "quiz",
            "options": validated["options"],
            "answer_index": validated["answer_index"],
            "explanation": validated["explanation"],
            "topic": mc.topic,
            "subject": mc.subject,
            "difficulty": mc.difficulty,
        },
        difficulty=mc.difficulty,
    )


def _build_behavioral_question(validated: dict, mc) -> Question:
    """Build a Question from validated behavioral data."""
    return Question(
        prompt=validated["prompt"],
        metadata={
            "type": "behavioral",
            "what_good_looks_like": validated["what_good_looks_like"],
            "topic": mc.topic,
            "subject": mc.subject,
            "difficulty": mc.difficulty,
        },
        difficulty=mc.difficulty,
    )


def _build_design_question(validated: dict, mc) -> Question:
    """Build a Question from validated design (LLD) data."""
    return Question(
        prompt=validated["scenario"],
        metadata={
            "type": "design",
            "requirements": validated["requirements"],
            "evaluation_rubric": validated["evaluation_rubric"],
            "topic": mc.topic,
            "subject": mc.subject,
            "difficulty": mc.difficulty,
        },
        difficulty=mc.difficulty,
    )


def _build_system_design_question(validated: dict, mc) -> Question:
    """Build a Question from validated system_design (HLD) data."""
    return Question(
        prompt=validated["scenario"],
        metadata={
            "type": "system_design",
            "functional_requirements": validated["functional_requirements"],
            "non_functional_requirements": validated["non_functional_requirements"],
            "evaluation_rubric": validated["evaluation_rubric"],
            "topic": mc.topic,
            "subject": mc.subject,
            "difficulty": mc.difficulty,
        },
        difficulty=mc.difficulty,
    )


# --------------------------------------------------------------------------- #
# Public generator functions — called by assessment_engine via registry
# --------------------------------------------------------------------------- #

async def generate_quiz_assessment(
    *,
    roadmap_node_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    target_company: Optional[str] = None,
    exclude_ids: Optional[List[str]] = None,
    **_ignored,
) -> Question:
    """Generate an MCQ/Theory question via AI, constrained by MissionContext."""
    return await _generate_via_ai(
        roadmap_node_id=roadmap_node_id,
        prompt_template_key="quiz",
        validate_fn=_validate_quiz_response,
        build_question_fn=_build_quiz_question,
        target_company=target_company,
    )


async def generate_behavioral_assessment(
    *,
    roadmap_node_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    target_company: Optional[str] = None,
    exclude_ids: Optional[List[str]] = None,
    **_ignored,
) -> Question:
    """Generate a behavioral interview question via AI, constrained by MissionContext."""
    return await _generate_via_ai(
        roadmap_node_id=roadmap_node_id,
        prompt_template_key="behavioral",
        validate_fn=_validate_behavioral_response,
        build_question_fn=_build_behavioral_question,
        target_company=target_company,
    )


async def generate_system_design_assessment(
    *,
    roadmap_node_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    target_company: Optional[str] = None,
    exclude_ids: Optional[List[str]] = None,
    **_ignored,
) -> Question:
    """Generate a design (LLD) or system_design (HLD) question via AI.

    The prompt template key is selected based on the roadmap node's original
    ``assessment_type`` string (resolved via ``build_mission_context``):
      * ``"design"`` → LLD/OOD prompt template
      * ``"system_design"`` → HLD scalable-systems prompt template

    Both map to ``AssessmentType.SYSTEM_DESIGN`` at the enum level.
    """
    # Resolve the LLD/HLD distinction from the roadmap node — deterministic.
    roadmap_assessment_type = None
    if roadmap_node_id:
        try:
            mc = build_mission_context(roadmap_node_id)
            roadmap_assessment_type = mc.assessment_type
        except Exception:
            pass

    if roadmap_assessment_type == "design":
        template_key = "design"
        validate_fn = _validate_design_response
        build_fn = _build_design_question
    else:
        template_key = "system_design"
        validate_fn = _validate_system_design_response
        build_fn = _build_system_design_question

    return await _generate_via_ai(
        roadmap_node_id=roadmap_node_id,
        prompt_template_key=template_key,
        validate_fn=validate_fn,
        build_question_fn=build_fn,
        target_company=target_company,
    )


# --------------------------------------------------------------------------- #
# Registration — generators are registered at module import time
# --------------------------------------------------------------------------- #

register_generator(AssessmentType.MCQ, generate_quiz_assessment)
register_generator(AssessmentType.THEORY, generate_quiz_assessment)
register_generator(AssessmentType.BEHAVIORAL, generate_behavioral_assessment)
register_generator(AssessmentType.SYSTEM_DESIGN, generate_system_design_assessment)
