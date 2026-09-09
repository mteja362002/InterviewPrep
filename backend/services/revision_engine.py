"""Canonical Revision Engine — single source of truth for spaced repetition.

This service owns spaced-repetition scheduling math and "what's due" queries
so Mission Engine, the Knowledge Base, and AI Mentor all consume the same
logic (mirrors the `services/streak_engine.py` pattern already used in this
codebase).

Revision state is stored directly on the canonical `knowledge_nodes` rows
(the same collection `services/progress_engine.py` owns) via the
`next_revision` / `revision_stage` fields — there is no parallel revision
store. The legacy `revisions` collection (`RevisionItem`) is no longer
written to by production code; it is kept, unmodified, purely so historical
data remains queryable.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from services.evidence import planner_row, certified_fields, LEGACY, ACTUAL
from services.progress_repository import upsert_progress_fields

REVISION_STAGES_DAYS = [1, 3, 7, 14, 30, 60]


def confidence_modifier_days(confidence: int) -> float:
    """Adjust default interval based on confidence 1-10."""
    if confidence <= 3:
        return 0.4  # revise much sooner
    if confidence <= 5:
        return 0.7
    if confidence >= 9:
        return 1.5  # can wait longer
    if confidence >= 7:
        return 1.2
    return 1.0


def schedule_next_revision(current_stage: int, confidence: int = 6) -> tuple[int, str]:
    """Return (next_stage, next_date_str)."""
    next_stage = min(current_stage + 1, len(REVISION_STAGES_DAYS) - 1)
    days = REVISION_STAGES_DAYS[next_stage] * confidence_modifier_days(confidence)
    days = max(1, round(days))
    d = (datetime.now(timezone.utc) + timedelta(days=days)).date().isoformat()
    return next_stage, d


def first_revision_date(confidence: int = 6) -> str:
    days = REVISION_STAGES_DAYS[0] * confidence_modifier_days(confidence)
    days = max(1, round(days))
    return (datetime.now(timezone.utc) + timedelta(days=days)).date().isoformat()


async def mark_node_for_revision(
    db, user_id: str, roadmap_version: str, node_id: str, confidence: int = 6,
) -> None:
    """Advance (or start) the spaced-repetition schedule for one canonical node.

    This is the only place that writes revision-scheduling state. It stamps
    `next_revision` / `revision_stage` directly onto the node's `knowledge_nodes`
    row (creating it if needed) instead of a separate revisions collection.
    """
    existing = await db.knowledge_nodes.find_one(
        {"user_id": user_id, "roadmap_version": roadmap_version, "node_id": node_id}, {"_id": 0},
    )
    # A historical schedule stays inspectable, but cannot certify an inherited
    # revision-stage count. The forward evidence schedule has its own history.
    existing = certified_fields(existing or {})
    if existing.get("next_revision"):
        current_stage = int(existing.get("revision_stage") or 0)
        next_stage, next_date = schedule_next_revision(current_stage, confidence)
    else:
        next_stage, next_date = 0, first_revision_date(confidence)

    await upsert_progress_fields(
        db, user_id=user_id, roadmap_version=roadmap_version, node_id=node_id,
        fields={"next_revision": next_date, "revision_stage": next_stage}, source="revision",
    )


async def get_revisions_for_user(
    db, user_id: str, roadmap_version: str, *,
    roadmap=None, limit: int = 20, due_only: bool = True,
) -> List[dict]:
    """Canonical "what's due for revision" query — single source across the app.

    Reads from `knowledge_nodes` (the Progress Engine's own collection) keyed
    by `next_revision`. Returns items shaped to match the legacy `revisions`
    collection's public fields (`task_title`, `topic`, `next_review_date`,
    `stage`, `is_due`) so existing consumers (mission generation, the
    `/api/revisions/queue` response, the dashboard revisions widget) need no
    further shape changes.
    """
    if roadmap is None:
        from roadmap import get_roadmap as _get_roadmap, CURRENT_VERSION as _CURRENT_VERSION
        roadmap = _get_roadmap(roadmap_version or _CURRENT_VERSION)

    today = datetime.now(timezone.utc).date().isoformat()
    # Both schedules remain usable; a new attributable schedule takes precedence.
    # Filter/sort after projection so a superseded legacy due date cannot win.
    from services.progress_engine import load_user_progress_rows
    raw_rows = await load_user_progress_rows(db, user_id, roadmap_version)
    rows = []
    for raw in raw_rows.values():
        row = planner_row(raw)
        due = row.get("next_revision")
        if due and (not due_only or due[:10] <= today):
            row["evidence_classification"] = ACTUAL if "next_revision" in certified_fields(raw) else LEGACY
            rows.append(row)
    rows = sorted(rows, key=lambda row: (row["next_revision"], row["node_id"]))[:limit]

    out: List[dict] = []
    for row in rows:
        node = roadmap.get(row["node_id"])
        label = node["label"] if node else row["node_id"]
        track = roadmap.find_track(row["node_id"]) if hasattr(roadmap, "find_track") else None
        topic = track["id"] if track else row["node_id"]
        next_review_date: Optional[str] = row.get("next_revision")
        out.append({
            "node_id": row["node_id"],
            "task_title": label,
            "topic": topic,
            "next_review_date": next_review_date,
            "stage": row.get("revision_stage", 0),
            "is_due": bool(next_review_date) and next_review_date <= today,
            "confidence": certified_fields(row).get("confidence"),
            "evidence_classification": row["evidence_classification"],
        })
    return out
