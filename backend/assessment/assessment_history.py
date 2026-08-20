"""Assessment History — persistence repository for the ``assessments`` collection.

WHY A NEW COLLECTION: assessment sessions/attempts/results/evidence are a
genuinely new domain entity. ``knowledge_nodes`` models per-node learning
progress and ``daily_missions`` models missions — neither can represent an
assessment's lifecycle, rubric, attempt, result, feedback, and evidence
without overloading their schema. A single normalized document per
assessment (aggregate root) keeps reads/writes simple and is the natural
normalized shape.

DB access mirrors the codebase convention (local ``from server import db``
to avoid an import cycle).
"""
from __future__ import annotations

from typing import List, Optional

from .schemas import Assessment

_COLLECTION = "assessments"


def _db():
    from server import db  # local import avoids circular import at load time
    return db


async def ensure_indexes() -> None:
    """Create indexes for common access patterns. Idempotent."""
    db = _db()
    await db[_COLLECTION].create_index("id", unique=True)
    await db[_COLLECTION].create_index([("user_id", 1), ("created_at", -1)])
    await db[_COLLECTION].create_index([("user_id", 1), ("mission_id", 1)])


async def save(assessment: Assessment) -> Assessment:
    """Upsert the assessment document by its id."""
    db = _db()
    doc = assessment.to_doc()
    await db[_COLLECTION].update_one({"id": doc["id"]}, {"$set": doc}, upsert=True)
    return assessment


async def get(user_id: str, assessment_id: str) -> Optional[Assessment]:
    db = _db()
    doc = await db[_COLLECTION].find_one(
        {"id": assessment_id, "user_id": user_id}, {"_id": 0},
    )
    return Assessment(**doc) if doc else None


async def list_for_user(
    user_id: str, *, limit: int = 50, mission_id: Optional[str] = None,
) -> List[Assessment]:
    db = _db()
    query: dict = {"user_id": user_id}
    if mission_id is not None:
        query["mission_id"] = mission_id
    cur = db[_COLLECTION].find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
    docs = await cur.to_list(length=limit)
    return [Assessment(**d) for d in docs]


async def list_evidence_for_user(user_id: str, *, limit: int = 200) -> List[dict]:
    """Return the evidence payloads for a user's evaluated assessments.

    This is the read surface Learner Intelligence (or future analytics) can
    consume WITHOUT the Assessment Engine ever pushing into planner state.
    """
    db = _db()
    cur = db[_COLLECTION].find(
        {"user_id": user_id, "evidence": {"$ne": None}}, {"_id": 0, "evidence": 1},
    ).sort("created_at", -1).limit(limit)
    docs = await cur.to_list(length=limit)
    return [d["evidence"] for d in docs if d.get("evidence")]
