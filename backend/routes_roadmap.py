"""Roadmap Engine API + Knowledge Graph endpoints."""
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException

from auth_utils import get_current_user
from models import (
    KnowledgeNode, KnowledgeNoteUpdate, KnowledgeConfidenceUpdate,
    KnowledgeStatusUpdate, KnowledgeAttemptUpdate,
)
from roadmap import get_roadmap, CURRENT_VERSION
from problem_bank import problem_by_id
from ai_service import AIProviderError
from knowledge_generation import ensure_content, read_cache, clear_cache
from services.progress_engine import build_canonical_progress, load_user_progress_rows, confidence_to_node_fields
from services.revision_engine import first_revision_date
from services.learning_engine.roi import compute_learning_roi
from services.learning_engine.ranking import _is_foundation_node
from mission_engine import compute_readiness

router = APIRouter(prefix="/api/roadmap", tags=["roadmap"])


# Status vocabulary — normalized public surface.
STATUS_NOT_STARTED = "not_started"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_MASTERED = "mastered"
STATUS_REVISION_DUE = "revision_due"

# Legacy `available` from earlier iterations maps to `not_started` on the
# public surface. We rewrite it on read; older rows keep working untouched.
_LEGACY_STATUS_MAP = {"available": STATUS_NOT_STARTED, "locked": STATUS_NOT_STARTED}


def _normalize_status(raw: Optional[str], next_revision: Optional[str]) -> str:
    st = _LEGACY_STATUS_MAP.get(raw or "", raw) or STATUS_NOT_STARTED
    # Derive `revision_due` when a completed/mastered node has a due date in the past.
    if st in (STATUS_COMPLETED, STATUS_MASTERED) and next_revision:
        try:
            due = datetime.fromisoformat(next_revision.replace("Z", "+00:00"))
            if due <= datetime.now(timezone.utc):
                return STATUS_REVISION_DUE
        except Exception:
            pass
    return st


def _clean(d: dict) -> dict:
    if d:
        d.pop("_id", None)
    return d


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _get_user_version(db, user_id: str) -> str:
    u = await db.users.find_one({"id": user_id}, {"roadmap_version": 1})
    return (u or {}).get("roadmap_version") or CURRENT_VERSION


async def _ensure_user_version(db, user_id: str) -> str:
    """Stamp user with current version if missing."""
    v = await _get_user_version(db, user_id)
    if not v:
        await db.users.update_one({"id": user_id}, {"$set": {"roadmap_version": CURRENT_VERSION}})
        return CURRENT_VERSION
    return v


def _bucket(confidence: float, weakness_score: float) -> str:
    """Legacy adapter — delegates to canonical bucket in score_to_node_fields."""
    from services.progress_engine import confidence_to_node_fields as _ctf
    return _ctf(confidence)["revision_bucket"]


async def _load_user_progress(db, user_id: str) -> dict:
    """Return dict node_id → KnowledgeNode doc.

    Delegates to the canonical Progress Engine loader (services/progress_engine.py)
    so every route module queries `knowledge_nodes` the same way.
    """
    return await load_user_progress_rows(db, user_id)


def _is_leaf_node(node: dict) -> bool:
    """A node is a leaf if it has no descendants — those are the units we count."""
    return not (node.get("child_ids") or [])


def _rollup_from_progress(node: dict, progress: dict, roadmap) -> dict:
    """Compute status + mastery + counts for a node from itself or its descendants."""
    is_leaf = _is_leaf_node(node)
    # Legacy migrations can insert a knowledge_nodes row keyed by a track/module
    # id (e.g. node_id == "dsa") from pre-roadmap per-track progress. Such a row
    # must never be treated as leaf-level progress for a non-leaf node — doing so
    # short-circuits the structural rollup and incorrectly zeroes total_topics.
    prog = progress.get(node["id"]) if is_leaf else None
    if prog:
        status = _normalize_status(prog.get("status"), prog.get("next_revision"))
        mastery = float(prog.get("mastery_percentage", 0.0))
        est_min = int(node.get("estimated_minutes") or 0)
        is_done = status in (STATUS_COMPLETED, STATUS_MASTERED)
        completed_topics = 1 if is_done else 0
        total_topics = 1
        remaining_minutes = 0 if is_done else est_min
        return {
            "status": status,
            "confidence": round(prog.get("confidence", 0.0), 2),
            "weakness_score": round(prog.get("weakness_score", 0.0), 2),
            "mastery_percentage": round(mastery, 2),
            "revision_bucket": prog.get("revision_bucket", "green"),
            "has_progress": True,
            "bookmarked": bool(prog.get("bookmarked", False)),
            "favorite": bool(prog.get("favorite", False)),
            "attempts": int(prog.get("attempts", 0)),
            "actual_solve_minutes": int(prog.get("actual_solve_minutes", 0)),
            "completion_date": prog.get("completion_date"),
            "last_revision": prog.get("last_revision"),
            "next_revision": prog.get("next_revision"),
            "total_topics": total_topics,
            "completed_topics": completed_topics,
            "remaining_topics": total_topics - completed_topics,
            "completion_pct": 100.0 if is_done else 0.0,
            "estimated_hours_remaining": round(remaining_minutes / 60.0, 2),
        }

    # The canonical engine is the authoritative rollup path; use it for parent nodes.
    if node.get("id") != "root":
        canonical = build_canonical_progress(roadmap, progress)
        return {
            **canonical.get(node["id"], {}),
            "revision_bucket": _bucket(
                canonical.get(node["id"], {}).get("confidence", 0.0),
                canonical.get(node["id"], {}).get("weakness_score", 0.0),
            ),
            "has_progress": bool(progress.get(node["id"])),
            "bookmarked": bool(progress.get(node["id"], {}).get("bookmarked", False)),
            "favorite": bool(progress.get(node["id"], {}).get("favorite", False)),
            "attempts": int(progress.get(node["id"], {}).get("attempts", 0)),
            "actual_solve_minutes": int(progress.get(node["id"], {}).get("actual_solve_minutes", 0)),
            "completion_date": progress.get(node["id"], {}).get("completion_date"),
            "last_revision": progress.get(node["id"], {}).get("last_revision"),
            "next_revision": progress.get(node["id"], {}).get("next_revision"),
        }

    # Fallback for synthetic root node.
    return {
        "status": STATUS_NOT_STARTED,
        "confidence": 0.0,
        "weakness_score": 0.0,
        "mastery_percentage": 0.0,
        "revision_bucket": "green",
        "has_progress": False,
        "bookmarked": False,
        "favorite": False,
        "attempts": 0,
        "actual_solve_minutes": 0,
        "completion_date": None,
        "last_revision": None,
        "next_revision": None,
        "total_topics": 0,
        "completed_topics": 0,
        "remaining_topics": 0,
        "completion_pct": 0.0,
        "estimated_hours_remaining": 0.0,
    }


def _shape_node(n: dict, progress_view: dict) -> dict:
    """Public shape returned in tree responses (no recursive children objects,
    only ids). Callers can descend using child_ids."""
    return {
        "id": n["id"],
        "label": n["label"],
        "description": n.get("description"),
        "type": n.get("type"),
        "parent_id": n.get("parent_id"),
        "depth": n.get("depth", 0),
        "child_ids": n.get("child_ids", []),
        "pattern": n.get("pattern"),
        "difficulty": n.get("difficulty"),
        "estimated_minutes": n.get("estimated_minutes"),
        "interview_importance": n.get("interview_importance"),
        "interview_frequency": n.get("interview_frequency"),
        "mastery_weight": n.get("mastery_weight"),
        "tags": n.get("tags", []),
        "company_importance": n.get("company_importance") or {},
        "problem_ids": n.get("problem_ids", []),
        "prerequisites": n.get("prerequisites", []),
        "related": n.get("related", []),
        "progress": progress_view,
    }


# ============ Tree ============

@router.get("")
async def get_full_roadmap(user=Depends(get_current_user)):
    """Returns the full roadmap tree with per-user progress rolled up."""
    from server import db
    version = await _ensure_user_version(db, user["id"])
    roadmap = get_roadmap(version)
    progress = await _load_user_progress(db, user["id"])

    tracks = []
    for track in roadmap.tracks():
        track_view = _shape_node(track, _rollup_from_progress(track, progress, roadmap))
        # Build nested modules → topics → subtopics (light)
        def hydrate(n):
            v = _shape_node(n, _rollup_from_progress(n, progress, roadmap))
            v["children"] = [hydrate(roadmap.get(c)) for c in n.get("child_ids", []) if roadmap.get(c)]
            return v
        track_view["children"] = [hydrate(roadmap.get(c)) for c in track["child_ids"] if roadmap.get(c)]
        tracks.append(track_view)

    return {"version": version, "companies": roadmap.tree().get("companies", []), "tracks": tracks}


# ============ Node detail (Deep Topic page) ============

@router.get("/nodes/{node_id}")
async def get_node_detail(node_id: str, user=Depends(get_current_user)):
    from server import db
    version = await _ensure_user_version(db, user["id"])
    roadmap = get_roadmap(version)
    node = roadmap.get(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    progress_map = await _load_user_progress(db, user["id"])
    node_progress = _rollup_from_progress(node, progress_map, roadmap)

    breadcrumb = [{"id": a["id"], "label": a["label"], "type": a.get("type")}
                  for a in roadmap.ancestors(node_id)]

    prereqs = [{
        "id": p["id"], "label": p["label"], "type": p.get("type"),
        "progress": _rollup_from_progress(p, progress_map, roadmap),
    } for p in roadmap.prerequisites(node_id)]

    related = [{
        "id": r["id"], "label": r["label"], "type": r.get("type"),
    } for r in roadmap.related(node_id)]

    # Linked problems (aggregate from this + descendants)
    problem_ids = roadmap.problems_for_node(node_id)
    problems = []
    for pid in problem_ids[:20]:
        p = problem_by_id(pid)
        if p:
            problems.append(p)

    # Assignments/feedback for this node's problems
    if problem_ids:
        cur = db.problem_assignments.find(
            {"user_id": user["id"], "problem_id": {"$in": problem_ids}}, {"_id": 0},
        ).sort("assigned_at", -1).limit(40)
        assignments = await cur.to_list(length=40)
    else:
        assignments = []

    fb_cur = db.problem_feedback.find(
        {"user_id": user["id"], "problem_id": {"$in": problem_ids} if problem_ids else {"$exists": False}},
        {"_id": 0},
    ).sort("submitted_at", -1).limit(20)
    feedback = await fb_cur.to_list(length=20)

    # Personal notes come from the direct KnowledgeNode row (if present)
    direct = progress_map.get(node_id) or {}
    notes = direct.get("notes")

    # Recent activity referencing this node (via description/title matches). Best-effort.
    activity_cur = db.activity_events.find(
        {"user_id": user["id"], "$or": [
            {"description": {"$regex": node["label"], "$options": "i"}},
            {"title": {"$regex": node["label"], "$options": "i"}},
        ]}, {"_id": 0},
    ).sort("ts", -1).limit(10)
    activity = await activity_cur.to_list(length=10)

    # Track
    track = roadmap.find_track(node_id)

    # RC1.3.5B · Part F — interview-intelligence metadata, derived live from
    # the existing ROI/ranking engines rather than hardcoded on the node.
    # `roi`/`is_foundation_entry` are graph-derived (never stale); `must_know`
    # is a simple threshold on the already-authored `interview_frequency`.
    node_roi = compute_learning_roi(node_id) if roadmap._is_learning_node(node) else None
    is_foundation_entry = _is_foundation_node(node)
    must_know = int(node.get("interview_frequency", 0) or 0) >= 5

    # Company importance — for display we blend the effective inherited
    # rating (LearningNode → Topic → Module → Track, first hit wins) with
    # the track's own rating so topics without differentiated per-node data
    # still surface the track's known company bias. This is a *view-only*
    # blend; the ranking engine keeps consuming
    # `roadmap.company_importance()` unchanged (which now itself walks the
    # full hierarchy as of RC1.3.1).
    companies = roadmap.tree().get("companies", [])
    track_ci = (track.get("company_importance") or {}) if track else {}
    company_importance = {}
    for c in companies:
        # `roadmap.company_importance` walks Node → Topic → Module → Track.
        # For the display blend we deliberately combine that inherited
        # value with the track-level anchor so uniform-per-node topics
        # still differentiate across companies.
        inherited = roadmap.company_importance(node_id, c)
        tv = int(track_ci.get(c, 0) or 0)
        if inherited and tv:
            blended = round(0.65 * inherited + 0.35 * tv)
        else:
            blended = inherited or tv
        company_importance[c] = max(0, min(5, int(blended)))

    return {
        "node": _shape_node(node, node_progress),
        "track": {"id": track["id"], "label": track["label"]} if track else None,
        "breadcrumb": breadcrumb,
        "prerequisites": prereqs,
        "related": related,
        "problems": [{
            **p,
            "assignment": next((a for a in assignments if a["problem_id"] == p["id"]), None),
            "feedback": next((f for f in feedback if f["problem_id"] == p["id"]), None),
        } for p in problems],
        "notes": notes,
        "company_importance": company_importance,
        "activity": activity,
        "assignments_count": len(assignments),
        "roi": node_roi,
        "is_foundation_entry": is_foundation_entry,
        "must_know": must_know,
        "learning_stage": node.get("learning_stage"),
    }


# ============ Progress ============

@router.get("/progress")
async def get_progress(user=Depends(get_current_user)):
    from server import db
    version = await _ensure_user_version(db, user["id"])
    roadmap = get_roadmap(version)
    progress_map = await _load_user_progress(db, user["id"])
    # Roll up per track and per module using the canonical backend engine.
    result = []
    for track in roadmap.tracks():
        modules = []
        for module in track.get("modules", []) or []:
            modules.append({
                "id": module["id"], "label": module["label"],
                "progress": _rollup_from_progress(module, progress_map, roadmap),
                "topic_count": len(module.get("topics", []) or []),
            })
        result.append({
            "id": track["id"], "label": track["label"], "icon": track.get("icon"),
            "progress": _rollup_from_progress(track, progress_map, roadmap),
            "modules": modules,
        })
    return {"version": version, "tracks": result}


# ============ Dashboard summary ============

@router.get("/summary")
async def get_summary(user=Depends(get_current_user)):
    """Compact rollup for the Mission Control dashboard strip.

    Returns overall percentages and topic counts across every track — this
    is what powers the "Overall DSA %, LLD %, HLD %" tiles without needing
    the caller to walk the full tree.
    """
    from server import db
    version = await _ensure_user_version(db, user["id"])
    roadmap = get_roadmap(version)
    progress_map = await _load_user_progress(db, user["id"])

    today = datetime.now(timezone.utc).date().isoformat()
    tracks_summary = []
    total_topics = 0
    total_completed = 0
    total_hours_remaining = 0.0

    for track in roadmap.tracks():
        roll = _rollup_from_progress(track, progress_map, roadmap)
        tracks_summary.append({
            "id": track["id"], "label": track["label"], "icon": track.get("icon"),
            "completion_pct": roll["completion_pct"],
            "mastery_percentage": roll["mastery_percentage"],
            "completed_topics": roll["completed_topics"],
            "total_topics": roll["total_topics"],
            "remaining_topics": roll["remaining_topics"],
            "estimated_hours_remaining": roll["estimated_hours_remaining"],
            "status": roll["status"],
            "revision_bucket": roll["revision_bucket"],
        })
        total_topics += roll["total_topics"]
        total_completed += roll["completed_topics"]
        total_hours_remaining += roll["estimated_hours_remaining"]

    overall_completion = round((total_completed / total_topics) * 100.0, 2) if total_topics else 0.0

    # Interview Readiness — single canonical formula (mission_engine.compute_readiness),
    # the same one that powers GET /api/dashboard. Tracks with no progress yet
    # are omitted so the onboarding self-assessment baseline is used for them,
    # exactly like the dashboard's calculation.
    onboarding_doc = await db.onboarding.find_one({"user_id": user["id"]}, {"_id": 0}) or {}
    readiness_inputs = [
        {"topic": t["id"], "score": t["mastery_percentage"]}
        for t in tracks_summary if t["status"] != STATUS_NOT_STARTED
    ]
    overall_readiness = compute_readiness(readiness_inputs, onboarding_doc)

    # Today's completed topics — count knowledge_nodes whose completion_date is today.
    today_completed_ids: list[str] = []
    for nid, prog in progress_map.items():
        cd = prog.get("completion_date")
        if cd and cd[:10] == today:
            today_completed_ids.append(nid)

    revision_due_count = sum(
        1 for _, p in progress_map.items()
        if _normalize_status(p.get("status"), p.get("next_revision")) == STATUS_REVISION_DUE
    )
    bookmarked_count = sum(1 for _, p in progress_map.items() if p.get("bookmarked"))
    favorite_count = sum(1 for _, p in progress_map.items() if p.get("favorite"))

    # Build canonical progress object (single source of truth for UI)
    # Map key tracks: dsa, lld, hld, core_cs (core_cs aggregates networks/os/dbms)
    # Use roadmap.track ids to find rolls
    def _get_track_roll(track_id):
        for t in tracks_summary:
            if t["id"] == track_id:
                return t
        return None

    core_components = ["computer_networks", "operating_systems", "dbms"]
    # Per-track progress
    tracks_progress = {}
    for tid in ("dsa", "lld", "hld"):
        tr = _get_track_roll(tid)
        if tr:
            completed = int(tr.get("completed_topics", 0))
            total = int(tr.get("total_topics", 0))
            pct = int(round((completed / total) * 100.0)) if total else 0
            tracks_progress[tid] = {"completed": completed, "total": total, "percentage": pct}
        else:
            tracks_progress[tid] = {"completed": 0, "total": 0, "percentage": 0}

    # Core CS aggregates
    core_completed = 0
    core_total = 0
    for comp in core_components:
        tr = _get_track_roll(comp)
        if tr:
            core_completed += int(tr.get("completed_topics", 0))
            core_total += int(tr.get("total_topics", 0))
    core_pct = int(round((core_completed / core_total) * 100.0)) if core_total else 0
    tracks_progress["core_cs"] = {"completed": core_completed, "total": core_total, "percentage": core_pct}

    progress_obj = {
        "overall": {"completed": int(total_completed), "total": int(total_topics), "percentage": int(round((total_completed / total_topics) * 100.0)) if total_topics else 0},
        "tracks": tracks_progress,
        "today": {"completed": len(today_completed_ids), "total": len(today_completed_ids)},
    }

    return {
        "version": version,
        "tracks": tracks_summary,
        "overall": {
            "completion_pct": overall_completion,
            "readiness": overall_readiness,
            "total_topics": total_topics,
            "completed_topics": total_completed,
            "remaining_topics": total_topics - total_completed,
            "estimated_hours_remaining": round(total_hours_remaining, 2),
        },
        "today": {
            "completed_count": len(today_completed_ids),
            "completed_ids": today_completed_ids[:50],
        },
        "counts": {
            "revision_due": revision_due_count,
            "bookmarked": bookmarked_count,
            "favorite": favorite_count,
        },
        "progress": progress_obj,
    }




# ============ Notes ============

@router.patch("/nodes/{node_id}/notes")
async def update_notes(node_id: str, payload: KnowledgeNoteUpdate, user=Depends(get_current_user)):
    from server import db
    version = await _ensure_user_version(db, user["id"])
    roadmap = get_roadmap(version)
    if not roadmap.get(node_id):
        raise HTTPException(status_code=404, detail="Node not found")

    await db.knowledge_nodes.update_one(
        {"user_id": user["id"], "node_id": node_id, "roadmap_version": version},
        {"$set": {"notes": payload.notes, "updated_at": _now_iso(),
                  "user_id": user["id"], "node_id": node_id, "roadmap_version": version}},
        upsert=True,
    )
    return {"ok": True, "node_id": node_id}


# ============ Confidence update ============

@router.post("/nodes/{node_id}/confidence")
async def update_confidence(node_id: str, payload: KnowledgeConfidenceUpdate, user=Depends(get_current_user)):
    from server import db
    version = await _ensure_user_version(db, user["id"])
    roadmap = get_roadmap(version)
    if not roadmap.get(node_id):
        raise HTTPException(status_code=404, detail="Node not found")

    conf = float(payload.confidence)
    fields = confidence_to_node_fields(conf)
    status = fields["status"]

    set_doc = {
        "user_id": user["id"], "node_id": node_id, "roadmap_version": version,
        **fields,
        "updated_at": _now_iso(),
    }
    # Stamp completion_date when transitioning into completed/mastered.
    if status in (STATUS_COMPLETED, STATUS_MASTERED):
        set_doc["completion_date"] = _now_iso()
    await db.knowledge_nodes.update_one(
        {"user_id": user["id"], "node_id": node_id, "roadmap_version": version},
        {"$set": set_doc},
        upsert=True,
    )
    return {"ok": True, "node_id": node_id, "confidence": conf, "status": status}


# ============ Explicit status ============

@router.post("/nodes/{node_id}/status")
async def update_status(node_id: str, payload: KnowledgeStatusUpdate, user=Depends(get_current_user)):
    from server import db
    version = await _ensure_user_version(db, user["id"])
    roadmap = get_roadmap(version)
    if not roadmap.get(node_id):
        raise HTTPException(status_code=404, detail="Node not found")

    status = payload.status
    now = _now_iso()
    set_doc = {
        "user_id": user["id"], "node_id": node_id, "roadmap_version": version,
        "status": status, "updated_at": now,
    }
    # When marking completed/mastered, snap sensible defaults if the row was empty.
    if status in (STATUS_COMPLETED, STATUS_MASTERED):
        set_doc["completion_date"] = now
        # Load existing row for confidence lookup and mastery baseline check.
        existing = await db.knowledge_nodes.find_one(
            {"user_id": user["id"], "node_id": node_id, "roadmap_version": version},
            {"mastery_percentage": 1, "confidence": 1},
        ) or {}
        # Schedule a first revision via canonical Revision Engine (confidence-adjusted).
        existing_conf = int(existing.get("confidence", 6))
        set_doc["next_revision"] = first_revision_date(existing_conf)
        # Bump mastery baseline if none yet.
        if not existing.get("mastery_percentage"):
            set_doc["mastery_percentage"] = 100.0 if status == STATUS_MASTERED else 80.0
        if not existing.get("confidence"):
            set_doc["confidence"] = 9.0 if status == STATUS_MASTERED else 7.0
    elif status == STATUS_REVISION_DUE:
        set_doc["next_revision"] = now
    await db.knowledge_nodes.update_one(
        {"user_id": user["id"], "node_id": node_id, "roadmap_version": version},
        {"$set": set_doc},
        upsert=True,
    )
    return {"ok": True, "node_id": node_id, "status": status}


# ============ Bookmark / Favorite toggles ============

async def _toggle_flag(db, user_id: str, version: str, node_id: str, field: str) -> bool:
    existing = await db.knowledge_nodes.find_one(
        {"user_id": user_id, "node_id": node_id, "roadmap_version": version},
        {field: 1},
    ) or {}
    new_val = not bool(existing.get(field, False))
    await db.knowledge_nodes.update_one(
        {"user_id": user_id, "node_id": node_id, "roadmap_version": version},
        {"$set": {
            "user_id": user_id, "node_id": node_id, "roadmap_version": version,
            field: new_val, "updated_at": _now_iso(),
        }},
        upsert=True,
    )
    return new_val


@router.post("/nodes/{node_id}/bookmark")
async def toggle_bookmark(node_id: str, user=Depends(get_current_user)):
    from server import db
    version = await _ensure_user_version(db, user["id"])
    roadmap = get_roadmap(version)
    if not roadmap.get(node_id):
        raise HTTPException(status_code=404, detail="Node not found")
    val = await _toggle_flag(db, user["id"], version, node_id, "bookmarked")
    return {"ok": True, "node_id": node_id, "bookmarked": val}


@router.post("/nodes/{node_id}/favorite")
async def toggle_favorite(node_id: str, user=Depends(get_current_user)):
    from server import db
    version = await _ensure_user_version(db, user["id"])
    roadmap = get_roadmap(version)
    if not roadmap.get(node_id):
        raise HTTPException(status_code=404, detail="Node not found")
    val = await _toggle_flag(db, user["id"], version, node_id, "favorite")
    return {"ok": True, "node_id": node_id, "favorite": val}


# ============ Attempt logging ============

@router.post("/nodes/{node_id}/attempt")
async def record_attempt(node_id: str, payload: KnowledgeAttemptUpdate, user=Depends(get_current_user)):
    from server import db
    version = await _ensure_user_version(db, user["id"])
    roadmap = get_roadmap(version)
    if not roadmap.get(node_id):
        raise HTTPException(status_code=404, detail="Node not found")

    inc_doc = {"attempts": 1}
    if payload.actual_minutes:
        inc_doc["actual_solve_minutes"] = int(payload.actual_minutes)

    await db.knowledge_nodes.update_one(
        {"user_id": user["id"], "node_id": node_id, "roadmap_version": version},
        {
            "$inc": inc_doc,
            "$set": {
                "user_id": user["id"], "node_id": node_id, "roadmap_version": version,
                "updated_at": _now_iso(),
            },
            # If this is a brand-new row, seed status to in_progress.
            "$setOnInsert": {"status": STATUS_IN_PROGRESS},
        },
        upsert=True,
    )
    row = await db.knowledge_nodes.find_one(
        {"user_id": user["id"], "node_id": node_id, "roadmap_version": version},
        {"_id": 0, "attempts": 1, "actual_solve_minutes": 1},
    ) or {}
    return {
        "ok": True, "node_id": node_id,
        "attempts": int(row.get("attempts", 0)),
        "actual_solve_minutes": int(row.get("actual_solve_minutes", 0)),
    }


# ============ Version + Migration status ============

@router.get("/version")
async def get_version(user=Depends(get_current_user)):
    from server import db
    version = await _ensure_user_version(db, user["id"])
    return {"user_version": version, "current_version": CURRENT_VERSION}


# ============ AI-generated Knowledge Base content ============

def _content_view(doc: Optional[dict]) -> dict:
    """Shape a cached KnowledgeContent document for API consumers.

    Missing sections come back as empty lists / None so the frontend can render
    without null-guards. `available` is a convenience flag for lazy UIs."""
    if not doc:
        return {
            "available": False,
            "theory": None,
            "examples": [],
            "interview_tips": [],
            "common_mistakes": [],
            "flashcards": [],
            "related_topics": [],
            "prerequisites": [],
            "generated_at": None, "updated_at": None,
        }
    return {
        "available": bool(doc.get("theory")),
        "theory": doc.get("theory"),
        "examples": doc.get("examples") or [],
        "interview_tips": doc.get("interview_tips") or [],
        "common_mistakes": doc.get("common_mistakes") or [],
        "flashcards": doc.get("flashcards") or [],
        "related_topics": doc.get("related_topics") or [],
        "prerequisites": doc.get("prerequisites") or [],
        "generated_at": doc.get("generated_at"),
        "updated_at": doc.get("updated_at"),
    }


def _ai_error_to_http(err: AIProviderError) -> HTTPException:
    return HTTPException(
        status_code=err.status_code or 500,
        detail={"error": err.kind, "message": str(err)},
    )


@router.get("/nodes/{node_id}/content")
async def get_node_content(node_id: str, user=Depends(get_current_user)):
    """Return cached AI content for a node — never triggers generation.
    Frontend calls this on tab open and only prompts the user to generate
    when `available` is false."""
    from server import db
    version = await _ensure_user_version(db, user["id"])
    if not get_roadmap(version).get(node_id):
        raise HTTPException(status_code=404, detail="Node not found")
    doc = await read_cache(db, node_id=node_id, roadmap_version=version)
    return _content_view(doc)


@router.post("/nodes/{node_id}/content/generate")
async def generate_node_content(node_id: str, user=Depends(get_current_user)):
    """Generate + cache AI content for a node. Idempotent on a cache hit
    (returns the existing doc without a new AI call)."""
    from server import db
    version = await _ensure_user_version(db, user["id"])
    if not get_roadmap(version).get(node_id):
        raise HTTPException(status_code=404, detail="Node not found")
    try:
        doc = await ensure_content(
            db, node_id=node_id, roadmap_version=version, user_id=user["id"], force=False,
        )
    except AIProviderError as e:
        raise _ai_error_to_http(e)
    return _content_view(doc)


@router.post("/nodes/{node_id}/content/regenerate")
async def regenerate_node_content(node_id: str, user=Depends(get_current_user)):
    """Explicit re-generation. Clears the cache row and calls the AI again."""
    from server import db
    version = await _ensure_user_version(db, user["id"])
    if not get_roadmap(version).get(node_id):
        raise HTTPException(status_code=404, detail="Node not found")
    try:
        await clear_cache(db, node_id=node_id, roadmap_version=version)
        doc = await ensure_content(
            db, node_id=node_id, roadmap_version=version, user_id=user["id"], force=True,
        )
    except AIProviderError as e:
        raise _ai_error_to_http(e)
    return _content_view(doc)

