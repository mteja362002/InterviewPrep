"""Assessment Engine — the orchestrator (application service).

Thin coordinator that sequences the single-responsibility modules:

    generator -> session -> evaluation -> feedback -> evidence -> recommendation

It owns NO scoring or rubric rules itself. It never touches the planner,
Learner Intelligence, missions, or company intelligence — it only produces
and persists assessment evidence.
"""
from __future__ import annotations

from typing import Optional

from . import assessment_history as history
from . import assessment_session as session
from .assessment_generator import generate_coding_assessment  # noqa: F401 (registers generator)
from .assessment_types import get_generator, is_implemented
from .difficulty import default_difficulty
from .evaluation_engine import evaluate
from .evidence import build_evidence
from .feedback_engine import build_feedback
from .recommendations import build_recommendation
from .rubrics import get_rubric
from .schemas import (
    Assessment, AssessmentStatus, AssessmentType, Attempt,
    CreateAssessmentRequest, SubmitAssessmentRequest,
)


async def create_assessment(
    *,
    user_id: str,
    req: CreateAssessmentRequest,
    position: Optional[str] = None,
    learner_context_snapshot: Optional[dict] = None,
) -> Assessment:
    """Create a PENDING assessment with a generated question + rubric."""
    difficulty = req.difficulty or default_difficulty(position)
    generator = get_generator(req.assessment_type)  # raises if unsupported
    question = generator(
        roadmap_node_id=req.roadmap_node_id,
        difficulty=difficulty,
        target_company=req.target_company,
    )
    rubric = get_rubric(req.assessment_type)

    assessment = Assessment(
        user_id=user_id,
        assessment_type=req.assessment_type,
        status=AssessmentStatus.PENDING,
        roadmap_node_id=req.roadmap_node_id,
        mission_id=req.mission_id,
        target_company=req.target_company,
        company_context={"target_company": req.target_company} if req.target_company else {},
        learner_context_snapshot=learner_context_snapshot or {
            "position": position, "difficulty": difficulty,
        },
        rubric=rubric,
        question=question,
    )
    await history.save(assessment)
    return assessment


async def start_assessment(user_id: str, assessment_id: str) -> Optional[Assessment]:
    a = await history.get(user_id, assessment_id)
    if a is None:
        return None
    session.start(a)
    await history.save(a)
    return a


async def submit_assessment(
    user_id: str, assessment_id: str, req: SubmitAssessmentRequest,
) -> Optional[Assessment]:
    a = await history.get(user_id, assessment_id)
    if a is None:
        return None
    # Count reattempts deterministically from history for this node/mission.
    prior = await history.list_for_user(user_id, limit=200)
    attempt_number = 1 + sum(
        1 for p in prior
        if p.id != a.id and p.roadmap_node_id == a.roadmap_node_id and p.attempt is not None
    )
    attempt = Attempt(
        passed_tests=req.passed_tests, total_tests=req.total_tests,
        edge_cases_passed=req.edge_cases_passed, edge_cases_total=req.edge_cases_total,
        claimed_time_complexity=req.claimed_time_complexity,
        time_taken_seconds=req.time_taken_seconds,
        explanation=req.explanation, code=req.code, solved=req.solved,
        metadata={"attempt_number": attempt_number},
    )
    session.submit(a, attempt)
    await history.save(a)
    return a


async def evaluate_assessment(user_id: str, assessment_id: str) -> Optional[Assessment]:
    """Run deterministic evaluation -> feedback -> evidence -> recommendation,
    then move the assessment to COMPLETED."""
    a = await history.get(user_id, assessment_id)
    if a is None:
        return None
    if a.attempt is None or a.rubric is None:
        return a  # nothing to evaluate; caller handles as 409 upstream

    result = evaluate(a.attempt, a.rubric, a.question)
    feedback = build_feedback(result, a.question)
    evidence = build_evidence(a, result, attempt=a.attempt, question=a.question)
    # Requirement: recommendations are derived from EVIDENCE, not the raw score.
    recommendation = build_recommendation(evidence, feedback)

    a.result = result
    a.feedback = feedback
    a.evidence = evidence
    a.recommendation = recommendation

    session.mark_evaluated(a)
    session.complete(a)
    await history.save(a)
    return a
