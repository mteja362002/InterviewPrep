"""Read-only API for evidence-derived Learner Intelligence (Phase 3B).

Additive observability endpoints (JSON, auth-guarded). They expose the
learner-state overlay and the append-only update history that the Assessment
→ Learner Intelligence flow produces. No planner / mission behavior is
touched by these routes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from auth_utils import get_current_user
from .update_repository import default_repository

router = APIRouter(prefix="/api/learner-intelligence", tags=["learner-intelligence"])


def _uid(user: dict) -> str:
    return user.get("id") or user.get("user_id")


@router.get("/updates")
async def list_updates(limit: int = 200, user=Depends(get_current_user)):
    """Append-only history of learner-state updates derived from assessments."""
    limit = max(1, min(limit, 500))
    repo = default_repository()
    updates = await repo.list_for_user(_uid(user), limit=limit)
    return [u.to_dict() for u in updates]


@router.get("/state")
async def learner_state(user=Depends(get_current_user)):
    """Aggregated learner-state overlay derived from assessment evidence."""
    repo = default_repository()
    return await repo.build_state(_uid(user))
