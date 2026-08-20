"""Append-only persistence for learner-intelligence updates (Phase 3B).

WHY A NEW COLLECTION (`learner_intelligence_updates`): this is the canonical,
APPEND-ONLY log of learner-state changes derived from assessment evidence — a
distinct concern from ``assessments`` (which stores immutable evidence) and
``knowledge_nodes`` (current learning progress the planner reads). Keeping it
separate preserves existing planner/revision behavior (they never read this)
and gives future analytics a clean, immutable history.

Append-only invariant: writes are INSERTS only — records are never updated or
deleted, mirroring the immutability of the evidence they derive from.
"""
from __future__ import annotations

from typing import List, Optional

from .learner_state import build_learner_state
from .learner_update import LearnerIntelligenceUpdate

_COLLECTION = "learner_intelligence_updates"


def _db():
    from server import db  # local import avoids circular import at load time
    return db


async def ensure_indexes() -> None:
    db = _db()
    await db[_COLLECTION].create_index("update_id", unique=True)
    await db[_COLLECTION].create_index([("user_id", 1), ("created_at", 1)])
    await db[_COLLECTION].create_index([("user_id", 1), ("roadmap_node_id", 1)])


class UpdateRepository:
    """Append-only repository for LearnerIntelligenceUpdate records."""

    async def append(self, update: LearnerIntelligenceUpdate) -> LearnerIntelligenceUpdate:
        # INSERT only — never update/replace (append-only history).
        await _db()[_COLLECTION].insert_one(update.to_dict())
        return update

    async def list_for_user(self, user_id: str, *, limit: int = 500) -> List[LearnerIntelligenceUpdate]:
        cur = _db()[_COLLECTION].find({"user_id": user_id}, {"_id": 0}).sort("created_at", 1).limit(limit)
        docs = await cur.to_list(length=limit)
        return [LearnerIntelligenceUpdate.from_dict(d) for d in docs]

    async def build_state(self, user_id: str, *, limit: int = 500) -> dict:
        updates = await self.list_for_user(user_id, limit=limit)
        return build_learner_state(updates)


_DEFAULT = UpdateRepository()


def default_repository() -> UpdateRepository:
    return _DEFAULT
