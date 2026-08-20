"""Phase 3C — Mission → Assessment Workflow orchestration.

The mission ORCHESTRATES the assessment checkpoint; it never evaluates
assessments, computes learner updates, or produces recommendations. It
reuses the existing Assessment Engine (Phase 3A) and the Assessment →
Learner Intelligence integration (Phase 3B) unchanged:

    Mission → Assessment → Assessment Engine → Learner Intelligence → Mission Completion

Everything here is additive and deterministic. Old missions (no linked
assessment) behave exactly as before.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from auth_utils import get_current_user
from assessment import assessment_engine as engine
from assessment import assessment_history as assessment_history
from assessment.schemas import CreateAssessmentRequest

router = APIRouter(prefix="/api", tags=["mission-assessment"])


def _clean(doc):
    if not doc:
        return doc
    doc.pop("_id", None)
    return doc


# --------------------------------------------------------------------------- #
# Workflow computation (deterministic, no side effects)
# --------------------------------------------------------------------------- #

def _non_assessment_tasks(mission_doc: dict) -> list:
    """All mission tasks (study / coding / revision). The assessment is NOT a
    task — it is the separate final checkpoint."""
    return list(mission_doc.get("tasks", []) or [])


def _study_tasks(mission_doc: dict) -> list:
    return [t for t in _non_assessment_tasks(mission_doc) if t.get("kind") in ("study", "revise")]


def _coding_tasks(mission_doc: dict) -> list:
    return [t for t in _non_assessment_tasks(mission_doc) if t.get("kind") == "practice"]


def _all_complete(tasks: list) -> bool:
    return bool(tasks) and all(t.get("completed") for t in tasks)


def _tasks_all_complete(mission_doc: dict) -> bool:
    tasks = _non_assessment_tasks(mission_doc)
    return bool(tasks) and all(t.get("completed") for t in tasks)


def _derive_assessment_context(mission_doc: dict) -> dict:
    """Pick the roadmap node + difficulty the assessment should target.

    Prefer a coding (practice) task's node, else a study task's node, else the
    mission focus topic. Reuses data already on the mission — no new generator.
    """
    node_id = None
    for t in _coding_tasks(mission_doc):
        if t.get("node_id"):
            node_id = t["node_id"]
            break
    if not node_id:
        for t in _study_tasks(mission_doc):
            if t.get("node_id"):
                node_id = t["node_id"]
                break
    if not node_id:
        # last resort: the mission's recommendation insight node, else topic
        insight = mission_doc.get("recommendation_insight") or {}
        node_id = insight.get("node_id") or insight.get("id") or mission_doc.get("focus_topic")
    return {"node_id": node_id, "difficulty": mission_doc.get("difficulty")}


async def _linked_assessment(db, mission_doc: dict, user_id: str):
    aid = mission_doc.get("assessment_id")
    if not aid:
        return None
    return await assessment_history.get(user_id, aid)


def _workflow_state(mission_doc: dict, assessment_status: Optional[str]) -> str:
    """Coarse, deterministic workflow stage for the UI."""
    if mission_doc.get("status") == "completed":
        return "mission_completed"
    study_done = _all_complete(_study_tasks(mission_doc)) or not _study_tasks(mission_doc)
    coding_done = _all_complete(_coding_tasks(mission_doc)) or not _coding_tasks(mission_doc)
    if assessment_status == "completed":
        return "assessment_completed"
    if assessment_status in ("started", "submitted", "evaluated"):
        return "assessment_in_progress"
    if study_done and coding_done:
        return "assessment_available"
    if study_done and not coding_done:
        return "study_complete"
    return "mission_started"


async def enrich_mission_assessment(db, mission_doc: dict, user_id: str) -> dict:
    """Populate the OPTIONAL Phase 3C fields on a mission document in place.

    Reads the linked assessment (source of truth) to mirror its status onto
    the mission. Never mutates the assessment. Safe for old missions.
    """
    try:
        assessment = await _linked_assessment(db, mission_doc, user_id)
        a_status = assessment.status if assessment else None
        if hasattr(a_status, "value"):
            a_status = a_status.value
        mission_doc["assessment_status"] = a_status
        mission_doc["assessment_available"] = _tasks_all_complete(mission_doc)
        mission_doc["workflow_state"] = _workflow_state(mission_doc, a_status)
    except Exception:  # pragma: no cover - defensive; never break mission reads
        pass
    return mission_doc


async def assert_assessment_allows_completion(db, mission_doc: dict, user_id: str) -> None:
    """Enforce the Phase 3C completion rule: if a mission has a linked
    assessment, it must be COMPLETED before the mission can complete.

    Backward compatible: missions WITHOUT a linked assessment are unaffected.
    """
    aid = mission_doc.get("assessment_id")
    if not aid:
        return
    assessment = await assessment_history.get(user_id, aid)
    status = assessment.status if assessment else None
    if hasattr(status, "value"):
        status = status.value
    if status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Assessment required — complete today's assessment before finishing the mission.",
        )


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #

@router.post("/missions/{mission_id}/assessment/generate")
async def generate_mission_assessment(mission_id: str, user=Depends(get_current_user)):
    """Generate (or return the existing) assessment for today's mission.

    Reuses the Assessment Engine — does NOT introduce a second generator.
    """
    from server import db
    doc = await db.daily_missions.find_one({"id": mission_id, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Mission not found")
    if doc.get("status") == "skipped":
        raise HTTPException(status_code=400, detail="Mission was skipped.")

    # Idempotent: if already linked, return it.
    existing = await _linked_assessment(db, doc, user["id"])
    if existing is not None:
        return {"mission_id": mission_id, "assessment": existing.to_doc()}

    # Gate: study + coding must be done before the checkpoint unlocks.
    if not _tasks_all_complete(doc):
        raise HTTPException(
            status_code=409,
            detail="Finish your study and coding tasks before taking the assessment.",
        )

    ctx = _derive_assessment_context(doc)
    onboarding = _clean(await db.onboarding.find_one({"user_id": user["id"]})) or {}
    companies = onboarding.get("target_companies") or []
    target_company = companies[0] if companies else None

    req = CreateAssessmentRequest(
        assessment_type="coding",
        roadmap_node_id=ctx["node_id"],
        mission_id=mission_id,
        target_company=target_company,
        difficulty=ctx["difficulty"],
    )
    assessment = await engine.create_assessment(
        user_id=user["id"], req=req, position=onboarding.get("current_position"),
    )

    await db.daily_missions.update_one(
        {"id": mission_id},
        {"$set": {"assessment_id": assessment.id, "assessment_status": "pending"}},
    )
    return {"mission_id": mission_id, "assessment": assessment.to_doc()}


@router.get("/missions/{mission_id}/assessment")
async def get_mission_assessment(mission_id: str, user=Depends(get_current_user)):
    """Return the assessment linked to a mission (404 if none generated yet)."""
    from server import db
    doc = await db.daily_missions.find_one({"id": mission_id, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Mission not found")
    assessment = await _linked_assessment(db, doc, user["id"])
    if assessment is None:
        raise HTTPException(status_code=404, detail="No assessment for this mission yet.")
    return assessment.to_doc()
