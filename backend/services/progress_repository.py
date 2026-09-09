"""Attributed forward writes. Historical top-level learning values stay untouched."""
from datetime import datetime, timezone

from services.evidence import FIELDS, SOURCES
from services.progress_engine import score_to_node_fields


async def upsert_progress_fields(db, *, user_id, roadmap_version, node_id, fields,
                                 source, increments=None):
    """Dotted writes preserve raw legacy and unrelated certified fields.

    Per-field stamps prevent a status/revision update from certifying old mastery.
    Atomic increments preserve concurrent attempt counts.
    """
    from roadmap import get_roadmap
    if source not in SOURCES or not (set(fields) | set(increments or {})) <= FIELDS:
        raise ValueError("Unsupported evidence source or field")
    roadmap = get_roadmap(roadmap_version)
    node = roadmap.get(node_id)
    if node is None:
        raise ValueError(f"Unknown node in pinned roadmap: {node_id}")
    now = datetime.now(timezone.utc).isoformat()
    set_doc = {
        "user_id": user_id, "roadmap_version": roadmap_version, "node_id": node_id,
        "track": node.get("track") or node_id,
        "progress_schema_version": 1,
        "updated_at": now,
        **{f"certified_progress.{key}": value for key, value in fields.items()},
    }
    for key in set(fields) | set(increments or {}):
        set_doc[f"certified_progress.field_sources.{key}"] = {"source": source, "recorded_at": now}
    update = {"$set": set_doc}
    if increments:
        update["$inc"] = {f"certified_progress.{key}": value for key, value in increments.items()}
    await db.knowledge_nodes.update_one(
        {"user_id": user_id, "roadmap_version": roadmap_version, "node_id": node_id},
        update, upsert=True,
    )


async def upsert_progress_from_score(db, *, user_id, roadmap_version, node_id, score,
                                      source, status_override=None, completion_date=None):
    """Score must use exclusively certified prior state/new evidence."""
    fields = score_to_node_fields(score)
    if status_override:
        fields["status"] = status_override
    if completion_date:
        fields["completion_date"] = completion_date
    await upsert_progress_fields(db, user_id=user_id, roadmap_version=roadmap_version,
                                 node_id=node_id, fields=fields, source=source)
    return fields


async def upsert_progress_from_confidence(db, *, user_id, roadmap_version, node_id,
                                         confidence, source, status_override=None, completion_date=None):
    return await upsert_progress_from_score(
        db, user_id=user_id, roadmap_version=roadmap_version, node_id=node_id,
        score=confidence * 10, source=source, status_override=status_override,
        completion_date=completion_date,
    )
