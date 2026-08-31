"""Progress Repository — canonical write abstraction for knowledge_nodes.

Sprint 1 (Architecture Consolidation): every progress write flows through
this module. No route, service, or engine may call ``db.knowledge_nodes``
write operations directly.

Read access remains via ``progress_engine.load_user_progress_rows()`` — this
module handles WRITES only.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from services.progress_engine import score_to_node_fields, confidence_to_node_fields


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def upsert_progress_from_score(
    db,
    *,
    user_id: str,
    roadmap_version: str,
    node_id: str,
    score: float,
    status_override: Optional[str] = None,
    completion_date: Optional[str] = None,
) -> dict:
    """Write derived progress fields from a 0-100 mastery score.

    Uses the canonical ``score_to_node_fields()`` — no inline formulas.
    ``status_override`` lets callers force a specific status (e.g. "completed"
    after solving a task, even if mastery alone would say "in_progress").
    """
    fields = score_to_node_fields(score)
    if status_override:
        fields["status"] = status_override
    now = _now_iso()
    set_doc = {
        **fields,
        "user_id": user_id,
        "roadmap_version": roadmap_version,
        "node_id": node_id,
        "updated_at": now,
    }
    if completion_date:
        set_doc["completion_date"] = completion_date
    await db.knowledge_nodes.update_one(
        {"user_id": user_id, "roadmap_version": roadmap_version, "node_id": node_id},
        {"$set": set_doc},
        upsert=True,
    )
    return fields


async def upsert_progress_from_confidence(
    db,
    *,
    user_id: str,
    roadmap_version: str,
    node_id: str,
    confidence: float,
    status_override: Optional[str] = None,
    completion_date: Optional[str] = None,
) -> dict:
    """Write derived progress fields from a 0-10 confidence value.

    Uses the canonical ``confidence_to_node_fields()`` — no inline formulas.
    """
    fields = confidence_to_node_fields(confidence)
    if status_override:
        fields["status"] = status_override
    now = _now_iso()
    set_doc = {
        **fields,
        "user_id": user_id,
        "roadmap_version": roadmap_version,
        "node_id": node_id,
        "updated_at": now,
    }
    if completion_date:
        set_doc["completion_date"] = completion_date
    await db.knowledge_nodes.update_one(
        {"user_id": user_id, "roadmap_version": roadmap_version, "node_id": node_id},
        {"$set": set_doc},
        upsert=True,
    )
    return fields


async def upsert_progress_fields(
    db,
    *,
    user_id: str,
    roadmap_version: str,
    node_id: str,
    fields: dict,
) -> None:
    """Write pre-computed fields (from score_to_node_fields) plus any extras.

    Low-level helper for callers that need to add extra fields (e.g. notes,
    mastery_percentage override, completion_date) on top of the canonical set.
    """
    now = _now_iso()
    set_doc = {
        **fields,
        "user_id": user_id,
        "roadmap_version": roadmap_version,
        "node_id": node_id,
        "updated_at": now,
    }
    await db.knowledge_nodes.update_one(
        {"user_id": user_id, "roadmap_version": roadmap_version, "node_id": node_id},
        {"$set": set_doc},
        upsert=True,
    )
