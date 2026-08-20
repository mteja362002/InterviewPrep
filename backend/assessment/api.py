"""Assessment Engine REST API (Phase 3A). JSON only, auth-guarded.

Routes under /api/assessments. The Assessment Engine produces evidence; it
never mutates planner / learner-intelligence / mission state.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from auth_utils import get_current_user
from . import assessment_engine as engine
from . import assessment_history as history
from .assessment_session import InvalidTransition
from .assessment_types import AssessmentTypeNotSupported
from .schemas import CreateAssessmentRequest, SubmitAssessmentRequest

router = APIRouter(prefix="/api/assessments", tags=["assessments"])


def _uid(user: dict) -> str:
    return user.get("id") or user.get("user_id")


@router.post("")
async def create_assessment(req: CreateAssessmentRequest, user=Depends(get_current_user)):
    try:
        a = await engine.create_assessment(
            user_id=_uid(user), req=req, position=user.get("current_position"),
        )
    except AssessmentTypeNotSupported as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return a.to_doc()


@router.get("/history")
async def assessment_history(limit: int = 50, mission_id: str = None, user=Depends(get_current_user)):
    limit = max(1, min(limit, 100))
    items = await history.list_for_user(_uid(user), limit=limit, mission_id=mission_id)
    return [a.to_doc() for a in items]


@router.get("/evidence")
async def user_evidence(limit: int = 100, user=Depends(get_current_user)):
    """All evidence for the user — the read surface Learner Intelligence consumes."""
    limit = max(1, min(limit, 200))
    return await history.list_evidence_for_user(_uid(user), limit=limit)


@router.post("/{assessment_id}/start")
async def start_assessment(assessment_id: str, user=Depends(get_current_user)):
    try:
        a = await engine.start_assessment(_uid(user), assessment_id)
    except InvalidTransition as e:
        raise HTTPException(status_code=409, detail=str(e))
    if a is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return a.to_doc()


@router.post("/{assessment_id}/submit")
async def submit_assessment(assessment_id: str, req: SubmitAssessmentRequest, user=Depends(get_current_user)):
    try:
        a = await engine.submit_assessment(_uid(user), assessment_id, req)
    except InvalidTransition as e:
        raise HTTPException(status_code=409, detail=str(e))
    if a is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return a.to_doc()


@router.post("/{assessment_id}/evaluate")
async def evaluate_assessment(assessment_id: str, user=Depends(get_current_user)):
    try:
        a = await engine.evaluate_assessment(_uid(user), assessment_id)
    except InvalidTransition as e:
        raise HTTPException(status_code=409, detail=str(e))
    if a is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if a.result is None:
        raise HTTPException(status_code=409, detail="Assessment has no submitted attempt to evaluate")
    # Phase 3B: hand the immutable evidence to Learner Intelligence (the
    # canonical consumer). Best-effort at the orchestration boundary so the
    # Assessment Engine stays a pure producer and completion never breaks if
    # the integration hiccups. The engine itself never touches planner/LI.
    if a.evidence is not None:
        try:
            from services.learner_intelligence.evidence_integration import ingest_evidence
            await ingest_evidence(a.evidence, user_id=_uid(user))
        except Exception:  # pragma: no cover - defensive; must not fail completion
            pass
    return a.to_doc()


@router.get("/{assessment_id}")
async def get_assessment(assessment_id: str, user=Depends(get_current_user)):
    a = await history.get(_uid(user), assessment_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return a.to_doc()


@router.get("/{assessment_id}/result")
async def get_result(assessment_id: str, user=Depends(get_current_user)):
    a = await history.get(_uid(user), assessment_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if a.result is None:
        raise HTTPException(status_code=404, detail="Assessment not evaluated yet")
    return a.result.model_dump(mode="json")


@router.get("/{assessment_id}/feedback")
async def get_feedback(assessment_id: str, user=Depends(get_current_user)):
    a = await history.get(_uid(user), assessment_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if a.feedback is None:
        raise HTTPException(status_code=404, detail="Assessment not evaluated yet")
    return a.feedback.model_dump(mode="json")


@router.get("/{assessment_id}/evidence")
async def get_evidence(assessment_id: str, user=Depends(get_current_user)):
    a = await history.get(_uid(user), assessment_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if a.evidence is None:
        raise HTTPException(status_code=404, detail="Assessment not evaluated yet")
    return a.evidence.model_dump(mode="json")
