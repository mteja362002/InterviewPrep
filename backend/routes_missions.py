"""Mission + Dashboard + Coding Arena + Feedback + Knowledge tree routes."""
from datetime import datetime, timezone, timedelta
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)

from auth_utils import get_current_user
from models import (
    DailyMission, MissionTask, StudyStreak,
    ActivityEvent, OnboardingPatch, OnboardingRecord,
    ProblemAssignment, ProblemFeedbackPayload, ProblemFeedback, MissionAdjustment,
    WeaknessRecord,
)
from mission_engine import (
    build_mission_for_user, today_date_str,
    compute_readiness, compute_company_readiness,
    apply_knowledge_gain, TOPIC_META, COMPANY_READINESS_WEIGHTS,
    determine_mode, analyze_recent_feedback,
)
from services.streak_engine import update_streak_on_completion, streak_days_grid
from services.progress_engine import (
    build_canonical_progress, load_user_progress_rows, score_to_node_fields,
    count_remaining_learning_nodes,
)
from services.revision_engine import get_revisions_for_user, mark_node_for_revision
from roadmap import get_roadmap, CURRENT_VERSION
from problem_bank import (
    PROBLEMS, PATTERN_TO_DOMAIN, pattern_counts, problems_by_pattern,
    problem_by_id,
)
from leetcode_catalog import get_by_id as catalog_get_by_id
from services.learning_engine.planner import get_today_learning_node
from services.learning_engine.pacing import compute_pacing_state

router = APIRouter(prefix="/api", tags=["missions"])


def _clean(doc: dict) -> dict:
    if doc:
        doc.pop("_id", None)
    return doc


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _log_activity(db, user_id: str, kind: str, title: str, description: str = None):
    ev = ActivityEvent(user_id=user_id, kind=kind, title=title, description=description)
    await db.activity_events.insert_one(ev.model_dump())


async def _get_streak(db, user_id: str) -> Optional[dict]:
    doc = await db.study_streaks.find_one({"user_id": user_id})
    return _clean(doc) if doc else None


async def _upsert_streak_on_completion(db, user_id: str) -> dict:
    existing = await _get_streak(db, user_id)
    updated_fields = update_streak_on_completion(existing)
    await db.study_streaks.update_one(
        {"user_id": user_id},
        {"$set": {**updated_fields, "user_id": user_id}},
        upsert=True,
    )
    return await _get_streak(db, user_id)


async def _get_onboarding(db, user_id: str) -> Optional[dict]:
    return _clean(await db.onboarding.find_one({"user_id": user_id}))


async def _require_onboarding(db, user_id: str) -> dict:
    """Fetch onboarding or self-heal + raise 409 to force wizard.

    Handles the corner case where a user has `users.onboarding_completed=true`
    but no matching row in `onboarding` (e.g. after DB cleanup or partial
    failures). We flip the user flag back so ProtectedRoute redirects to
    /onboarding on next auth check.
    """
    doc = await _get_onboarding(db, user_id)
    if doc:
        return doc
    await db.users.update_one(
        {"id": user_id}, {"$set": {"onboarding_completed": False}}
    )
    raise HTTPException(
        status_code=409,
        detail="onboarding_required",
    )


async def _get_knowledge(db, user_id: str) -> list:
    """Per-track scores derived from the canonical Progress Engine.

    Replaces the legacy per-track `knowledge_progress` collection as the read
    path — see services/progress_engine.py. Keeps the same List[dict] shape
    (topic/score/completions) so every existing caller (readiness formulas,
    dashboard knowledge_view, legacy topic selection) needs no changes.
    Topics with no progress yet are omitted so callers fall back to the
    onboarding self-assessment baseline, exactly like the legacy collection
    (which simply had no row for untouched topics).
    """
    roadmap = get_roadmap()
    progress_rows = await load_user_progress_rows(db, user_id)
    canonical = build_canonical_progress(roadmap, progress_rows)
    result = []
    for t in roadmap.track_ids():
        roll = canonical.get(t) or {}
        if roll.get("status", "not_started") == "not_started":
            continue
        result.append({
            "topic": t,
            "score": roll.get("mastery_percentage", 0.0),
            "completions": roll.get("completed_topics", 0),
        })
    return result


async def _get_due_revisions(db, user_id: str) -> list:
    """Delegates to the canonical Revision Engine (services/revision_engine.py)."""
    return await get_revisions_for_user(db, user_id, CURRENT_VERSION, limit=20, due_only=True)


async def _get_recent_feedback(db, user_id: str, hours: int = 48) -> list:
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    cur = db.problem_feedback.find(
        {"user_id": user_id, "submitted_at": {"$gte": since}}, {"_id": 0},
    ).sort("submitted_at", -1).limit(50)
    return await cur.to_list(length=50)


async def _count_extra_practice_yesterday(db, user_id: str) -> int:
    y = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    return await db.problem_assignments.count_documents({
        "user_id": user_id,
        "source": "practice_more",
        "assigned_at": {"$gte": f"{y}T00:00:00", "$lt": f"{y}T23:59:59"},
    })


async def _get_recent_mission_node_ids(db, user_id: str, days: int = 5) -> list:
    """Return study/practice node ids from the learner's last few missions.

    Foundation RC1.2 item 6 (recommendation diversity): reuses the existing
    `daily_missions` collection — no new history store — so
    `get_today_learning_node` can lightly deprioritize repeating the same
    node without touching prerequisite/unlock logic.
    """
    since = (datetime.now(timezone.utc).date() - timedelta(days=days)).isoformat()
    cur = db.daily_missions.find(
        {"user_id": user_id, "date": {"$gte": since}}, {"tasks.node_id": 1, "_id": 0},
    )
    node_ids = []
    async for doc in cur:
        for task in doc.get("tasks", []) or []:
            if task.get("node_id"):
                node_ids.append(task["node_id"])
    return node_ids


async def _get_recent_skipped_node_ids(db, user_id: str, days: int = 7) -> list:
    """Return node ids that appeared in missions the learner SKIPPED recently.

    RC1.3.3 · Skipped missions should be *deferred*, not immediately
    replaced (the previous behaviour blindly picked another node from
    the same pool). We surface the skipped nodes to the ranking engine
    so it can apply `_SKIP_DEFERRAL_PENALTY` — a moderate deprioritise
    that lets the pool rotate before those nodes come back around.

    Reuses `daily_missions` — the only place skip state is durable —
    so no new collection is required. Bounded to the last week so a
    node that was skipped once six months ago can still resurface
    naturally.
    """
    since = (datetime.now(timezone.utc).date() - timedelta(days=days)).isoformat()
    cur = db.daily_missions.find(
        {"user_id": user_id, "date": {"$gte": since}, "status": "skipped"},
        {"tasks.node_id": 1, "_id": 0},
    )
    node_ids: list = []
    async for doc in cur:
        for task in doc.get("tasks", []) or []:
            if task.get("node_id"):
                node_ids.append(task["node_id"])
    return node_ids


async def _get_recent_track_ids(db, user_id: str, limit: int = 4) -> list:
    """Return the ORDERED list of primary tracks (newest last) from the
    learner's recent missions.

    RC1.3.3 · Powers the same-track fatigue penalty. We deliberately
    return newest-last so `ranking.score_learning_node` can inspect
    the tail (``recent_track_ids[-1] == recent_track_ids[-2]``) to
    detect two consecutive same-track missions without also flagging
    a single day of same-track continuity.

    Only ``focus_topic`` is read — the same field the mission engine
    already writes on every mission. No schema change.
    """
    cur = db.daily_missions.find(
        {"user_id": user_id, "focus_topic": {"$ne": None}},
        {"focus_topic": 1, "date": 1, "_id": 0},
    ).sort("date", -1).limit(limit)
    docs = await cur.to_list(length=limit)
    # docs is newest-first; reverse so we return oldest-first (newest last),
    # matching the contract documented in `ranking.py`.
    tracks = [d.get("focus_topic") for d in docs if d.get("focus_topic")]
    tracks.reverse()
    return tracks


def _progress_node_id_for_task(task: dict) -> str:
    """Return the concrete roadmap node represented by a mission task.

    New missions carry ``node_id`` for roadmap-backed tasks. Keep the track
    fallback for historical mission documents that were created before node
    linkage existed.
    """
    node_id = task.get("node_id")
    if node_id and get_roadmap(CURRENT_VERSION).get(node_id):
        return node_id
    return task["topic"]


async def _record_completed_task_progress(
    db, user_id: str, task: dict, difficulty: str, baseline: dict, now: str,
) -> str:
    """Persist one completed task on the canonical per-node progress row."""
    node_id = _progress_node_id_for_task(task)
    existing_node = await db.knowledge_nodes.find_one(
        {"user_id": user_id, "roadmap_version": CURRENT_VERSION, "node_id": node_id}, {"_id": 0},
    )
    baseline_score = baseline.get(task["topic"], 5) * 10
    current = float(existing_node["mastery_percentage"]) if existing_node else float(baseline_score)
    new_score = apply_knowledge_gain(current, difficulty, task["kind"])
    fields = score_to_node_fields(new_score)
    await db.knowledge_nodes.update_one(
        {"user_id": user_id, "roadmap_version": CURRENT_VERSION, "node_id": node_id},
        {"$set": {
            **fields,
            "user_id": user_id, "roadmap_version": CURRENT_VERSION, "node_id": node_id,
            "status": "completed", "completion_date": now, "updated_at": now,
        }},
        upsert=True,
    )
    await mark_node_for_revision(db, user_id, CURRENT_VERSION, node_id)
    return node_id


async def _assignment_progress_node_id(db, assignment: dict) -> Optional[str]:
    """Find the concrete mission node behind a coding assignment, if any."""
    mission_id = assignment.get("mission_id")
    if not mission_id:
        return None
    mission = await db.daily_missions.find_one({"id": mission_id}, {"tasks": 1})
    if not mission:
        return None
    for task in mission.get("tasks", []):
        if task.get("kind") == "practice" and task.get("pattern") == assignment.get("pattern"):
            return _progress_node_id_for_task(task)
    return None


async def _attach_problems_to_mission(db, mission: DailyMission) -> None:
    """For any practice task with `pattern`, create ProblemAssignment records."""
    for task in mission.tasks:
        if task.kind != "practice" or not task.pattern:
            continue
        count = task.problem_count or 2
        # Pick unseen problems for user in this pattern
        seen_ids = set()
        cur = db.problem_assignments.find(
            {"user_id": mission.user_id, "pattern": task.pattern}, {"problem_id": 1, "_id": 0}
        )
        async for row in cur:
            seen_ids.add(row["problem_id"])
        pool = [p for p in problems_by_pattern(task.pattern) if p["id"] not in seen_ids]
        if not pool:
            # fall back to entire pool
            pool = problems_by_pattern(task.pattern)
        chosen = pool[:count]
        for p in chosen:
            assignment = ProblemAssignment(
                user_id=mission.user_id, problem_id=p["id"],
                mission_id=mission.id, pattern=task.pattern, source="mission",
            )
            await db.problem_assignments.insert_one(assignment.model_dump())


async def _generate_today_mission(db, user_id: str) -> DailyMission:
    onboarding = await _require_onboarding(db, user_id)
    knowledge = await _get_knowledge(db, user_id)
    knowledge_node_rows = await db.knowledge_nodes.find(
        {"user_id": user_id}, {"_id": 0}
    ).to_list(length=2000)
    knowledge_nodes = {row["node_id"]: row for row in knowledge_node_rows}
    revisions_due = await _get_due_revisions(db, user_id)
    recent_feedback = await _get_recent_feedback(db, user_id, hours=36)
    extra_yesterday = await _count_extra_practice_yesterday(db, user_id)
    recent_node_ids = await _get_recent_mission_node_ids(db, user_id)
    # RC1.3.3 · Adaptive mission consistency signals — cheap lookups from
    # the existing `daily_missions` collection, no new store.
    skipped_node_ids = await _get_recent_skipped_node_ids(db, user_id)
    recent_track_ids = await _get_recent_track_ids(db, user_id)

    remaining_curriculum = count_remaining_learning_nodes(get_roadmap(), knowledge_nodes)
    pacing_state = compute_pacing_state(
        onboarding.get("interview_target_date"),
        onboarding.get("daily_study_hours"),
        remaining_curriculum,
    )

    # ---- Learning recommendation with continuity + readiness estimate ----
    # `recent_completions` feeds continuity_score; sorted newest-first so
    # `chain_from_history` picks up yesterday's last touched node.
    recent_completions = sorted(
        [row for row in knowledge_node_rows if row.get("completion_date")],
        key=lambda r: r.get("completion_date") or "",
        reverse=True,
    )

    async def _pick_learning_recommendation(skip_ids=None):
        return await get_today_learning_node(
            user_id, db=db, pacing_state=pacing_state,
            target_companies=onboarding.get("target_companies"),
            completed_dates=[row.get("completion_date") for row in knowledge_node_rows if row.get("completion_date")],
            recent_node_ids=recent_node_ids,
            onboarding=onboarding,
            knowledge_rows=knowledge,
            recent_completions=recent_completions,
            skip_node_ids=skip_ids,
            skipped_node_ids=skipped_node_ids,
            recent_track_ids=recent_track_ids,
            company_intelligence=True,
        )

    learning_recommendation = await _pick_learning_recommendation()

    # ---- Build mission (first attempt) ------------------------------------
    mission, adjustment = build_mission_for_user(
        user_id, onboarding, knowledge, revisions_due,
        recent_feedback=recent_feedback,
        extra_practice_count_yesterday=extra_yesterday,
        knowledge_nodes=knowledge_nodes,
        learning_recommendation=learning_recommendation,
        pacing_state=pacing_state,
    )

    # ---- Regenerate once if validator flagged a hard failure --------------
    validation = adjustment.get("validation") or {}
    if validation.get("severity") == "regenerate":
        skip = set(validation.get("hint_skip_node_ids") or [])
        primary_id = (learning_recommendation or {}).get("node_id")
        if primary_id:
            skip.add(primary_id)
        alt = await _pick_learning_recommendation(skip_ids=skip)
        if alt is not None:
            mission_retry, adjustment_retry = build_mission_for_user(
                user_id, onboarding, knowledge, revisions_due,
                recent_feedback=recent_feedback,
                extra_practice_count_yesterday=extra_yesterday,
                knowledge_nodes=knowledge_nodes,
                learning_recommendation=alt,
                pacing_state=pacing_state,
            )
            retry_severity = (adjustment_retry.get("validation") or {}).get("severity")
            # Only accept the retry if it's strictly better than the first.
            if retry_severity in ("ok", "warn"):
                mission, adjustment = mission_retry, adjustment_retry
                adjustment["validation"]["regenerated"] = True
                adjustment["validation"].setdefault("previous_issues", validation.get("issues", []))

    await db.daily_missions.insert_one(mission.model_dump())
    await _attach_problems_to_mission(db, mission)

    # Persist adjustment (adaptive audit trail)
    adj = MissionAdjustment(
        user_id=user_id, for_date=mission.date,
        reason=adjustment["reason"],
        detected_weaknesses=adjustment["detected_weaknesses"],
        inserted_prerequisites=adjustment["inserted_prerequisites"],
        advance=adjustment["advance"],
        composition=adjustment.get("composition"),
        validation=adjustment.get("validation"),
    )
    await db.mission_adjustments.insert_one(adj.model_dump())

    await _log_activity(
        db, user_id, "mission_generated",
        f"Today's mission: {mission.title}",
        description=mission.focus_area,
    )

    # Adaptive Mission Engine (Sprint · iter 13): enrich with AI narrative +
    # tomorrow preview + week goal. Silent no-op if AI is unavailable.
    try:
        from ai_mentor.mission_planner import enrich_mission
        mission_doc = mission.model_dump()
        enriched = await enrich_mission(db, user_id=user_id, mission_doc=mission_doc)
        if enriched is not mission_doc:
            mission = DailyMission(**_clean(enriched)) if _clean(enriched) else mission
        else:
            for k in ("ai_narrative", "tomorrow_preview", "week_goal"):
                if enriched.get(k) is not None:
                    setattr(mission, k, enriched[k])
    except Exception as e:  # noqa: BLE001 — never let AI kill mission gen
        logger.warning("mission_planner enrichment failed: %s", e)

    return mission


# ============ Today's Mission ============

@router.get("/missions/today", response_model=DailyMission)
async def get_todays_mission(user=Depends(get_current_user)):
    from server import db
    today = today_date_str()
    doc = await db.daily_missions.find_one({"user_id": user["id"], "date": today})
    if doc:
        mission = DailyMission(**_clean(doc))
        # Lazy-enrich existing missions that pre-date the Adaptive Mission
        # Engine (or where the AI layer was unavailable on generation day).
        if not (mission.ai_narrative or mission.tomorrow_preview or mission.week_goal):
            try:
                from ai_mentor.mission_planner import enrich_mission
                enriched = await enrich_mission(db, user_id=user["id"], mission_doc=_clean(doc))
                for k in ("ai_narrative", "tomorrow_preview", "week_goal"):
                    if enriched.get(k) is not None:
                        setattr(mission, k, enriched[k])
            except Exception as e:  # noqa: BLE001
                logger.warning("mission_planner lazy-enrich failed: %s", e)
        return mission
    return await _generate_today_mission(db, user["id"])


# ============ Task toggle (replaces one-way complete) ============

@router.post("/missions/{mission_id}/tasks/{task_id}/toggle", response_model=DailyMission)
async def toggle_task(mission_id: str, task_id: str, user=Depends(get_current_user)):
    from server import db
    doc = await db.daily_missions.find_one({"id": mission_id, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Mission not found")
    if doc["status"] == "skipped":
        raise HTTPException(status_code=400, detail="Mission was skipped.")

    # RC1.3.1 · Mission-completion immutability:
    # Once a mission has been marked completed, individual tasks become
    # read-only. This prevents the completed → in_progress regression that
    # was corrupting streaks, notifications and planner history when users
    # (accidentally or otherwise) unchecked a task on an already-completed
    # mission. Admins can still force-reset via a future admin endpoint —
    # regular users must never observe the transition go backwards.
    if doc["status"] == "completed":
        raise HTTPException(
            status_code=409,
            detail="Mission already completed — tasks are locked.",
        )

    task = next((t for t in doc["tasks"] if t["id"] == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["completed"]:
        # UNCHECK — reverse. Safe because the mission cannot be `completed`
        # at this point (guarded above); the un-check therefore only
        # affects an in-progress mission.
        task["completed"] = False
        task["completed_at"] = None
        await db.daily_missions.update_one(
            {"id": mission_id},
            {"$set": {"tasks": doc["tasks"]}},
        )
        await _log_activity(db, user["id"], "task_uncompleted", f"Uncompleted: {task['title']}")
    else:
        # CHECK — mark complete + knowledge gain + spaced repetition.
        # Both are written directly onto the canonical `knowledge_nodes` row
        # (services/progress_engine.py / services/revision_engine.py) keyed
        # by the task's track id — there is no longer a parallel
        # knowledge_progress / revisions write for this event.
        task["completed"] = True
        task["completed_at"] = _now_iso()

        onboarding = await _get_onboarding(db, user["id"])
        await _record_completed_task_progress(
            db, user["id"], task, doc["difficulty"],
            (onboarding or {}).get("self_assessment", {}), task["completed_at"],
        )

        await db.daily_missions.update_one(
            {"id": mission_id}, {"$set": {"tasks": doc["tasks"]}},
        )
        await _log_activity(db, user["id"], "task_completed", f"Completed: {task['title']}")

    updated = await db.daily_missions.find_one({"id": mission_id})
    return DailyMission(**_clean(updated))


# Backwards-compat one-way complete (kept for API stability)
@router.post("/missions/{mission_id}/tasks/{task_id}/complete", response_model=DailyMission)
async def complete_task(mission_id: str, task_id: str, user=Depends(get_current_user)):
    return await toggle_task(mission_id, task_id, user)


# ============ Mission complete / skip ============

@router.post("/missions/{mission_id}/complete", response_model=DailyMission)
async def complete_mission(mission_id: str, user=Depends(get_current_user)):
    """RC1.3.1 · Complete a mission — idempotent + atomic.

    * If the mission is already `completed`, we short-circuit with the
      existing document. No streak bump, no duplicate notification, no
      duplicate planner event, no re-record of task progress.
    * If the mission was `skipped`, refuse the transition (cannot un-skip
      via completion — a skip is terminal for the day).
    * Guards against duplicate completion requests by claiming the
      terminal state via a conditional `find_one_and_update` (compare-
      and-swap on `status`) BEFORE performing any side-effects. Two
      concurrent completion calls therefore have exactly one winner; the
      loser sees the already-completed document.
    """
    from server import db
    doc = await db.daily_missions.find_one({"id": mission_id, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Mission not found")
    if doc["status"] == "completed":
        return DailyMission(**_clean(doc))
    if doc["status"] == "skipped":
        raise HTTPException(status_code=409, detail="Mission was skipped — cannot complete.")

    now = _now_iso()
    onboarding = await _get_onboarding(db, user["id"])
    baseline = (onboarding or {}).get("self_assessment", {})

    # Mark any pending tasks complete and record their per-node progress
    # BEFORE we flip the mission status — that way if the write fails the
    # mission stays in_progress and can be retried without duplicating
    # streak/notification side-effects.
    for t in doc["tasks"]:
        if not t["completed"]:
            t["completed"] = True
            t["completed_at"] = now
            await _record_completed_task_progress(
                db, user["id"], t, doc["difficulty"], baseline, now,
            )

    # Atomic compare-and-swap: only the first caller flips the state to
    # `completed`. This eliminates the "double streak / double
    # notification" race that appeared when the UI double-submitted.
    claim = await db.daily_missions.find_one_and_update(
        {"id": mission_id, "status": {"$ne": "completed"}},
        {"$set": {"status": "completed", "completed_at": now, "tasks": doc["tasks"]}},
        return_document=True,
    )
    if claim is None:
        # Another request already completed it — return the winning state.
        winner = await db.daily_missions.find_one({"id": mission_id})
        return DailyMission(**_clean(winner))

    # Side effects — only ever fired by the claim winner.
    await _upsert_streak_on_completion(db, user["id"])
    await _log_activity(
        db, user["id"], "mission_completed",
        f"Mission completed: {doc['title']}", description=doc["focus_area"],
    )
    updated = await db.daily_missions.find_one({"id": mission_id})
    return DailyMission(**_clean(updated))


@router.post("/missions/{mission_id}/skip", response_model=DailyMission)
async def skip_mission(mission_id: str, user=Depends(get_current_user)):
    from server import db
    doc = await db.daily_missions.find_one({"id": mission_id, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Mission not found")
    if doc["status"] != "in_progress":
        return DailyMission(**_clean(doc))
    now = _now_iso()
    await db.daily_missions.update_one(
        {"id": mission_id}, {"$set": {"status": "skipped", "skipped_at": now}},
    )
    await _log_activity(
        db, user["id"], "mission_skipped",
        f"Mission skipped: {doc['title']}", description=doc["focus_area"],
    )
    updated = await db.daily_missions.find_one({"id": mission_id})
    return DailyMission(**_clean(updated))


# ============ History ============

@router.get("/missions/history")
async def get_mission_history(limit: int = 20, user=Depends(get_current_user)):
    from server import db
    cur = db.daily_missions.find({"user_id": user["id"]}, {"_id": 0}).sort("date", -1).limit(limit)
    docs = await cur.to_list(length=limit)
    return [DailyMission(**d) for d in docs]


# ============ Revisions / Activity ============

@router.get("/revisions/queue")
async def get_revision_queue(user=Depends(get_current_user)):
    from server import db
    return await get_revisions_for_user(db, user["id"], CURRENT_VERSION, limit=20, due_only=False)


@router.get("/activity")
async def get_activity(limit: int = 20, user=Depends(get_current_user)):
    from server import db
    cur = db.activity_events.find({"user_id": user["id"]}, {"_id": 0}).sort("ts", -1).limit(limit)
    return await cur.to_list(length=limit)


# ============ Coding Arena ============

@router.get("/problems/patterns")
async def get_pattern_catalog():
    counts = pattern_counts()
    result = []
    for pattern, count in counts.items():
        domain, label = PATTERN_TO_DOMAIN.get(pattern, ("dsa", pattern))
        result.append({
            "pattern": pattern,
            "label": label,
            "domain": domain,
            "count": count,
        })
    result.sort(key=lambda x: -x["count"])
    return result


@router.get("/problems/{problem_id}")
async def get_problem(problem_id: str, user=Depends(get_current_user)):
    p = problem_by_id(problem_id)
    if not p:
        raise HTTPException(status_code=404, detail="Problem not found")
    return p


@router.get("/coding-arena")
async def get_coding_arena(user=Depends(get_current_user)):
    """Returns today's mission problems + user's active pattern + recent history."""
    from server import db
    # Self-heal onboarding-required inconsistency before touching any collection.
    await _require_onboarding(db, user["id"])
    today = today_date_str()

    # Today's mission
    mission_doc = await db.daily_missions.find_one({"user_id": user["id"], "date": today})
    if not mission_doc:
        # generate on demand
        await _generate_today_mission(db, user["id"])
        mission_doc = await db.daily_missions.find_one({"user_id": user["id"], "date": today})

    mission = DailyMission(**_clean(mission_doc))

    # Assignments for today's mission
    cur = db.problem_assignments.find(
        {"user_id": user["id"], "mission_id": mission.id}, {"_id": 0},
    )
    assignments = await cur.to_list(length=50)

    # Determine primary pattern (first DSA practice task)
    primary_pattern = None
    for t in mission.tasks:
        if t.kind == "practice" and t.pattern:
            primary_pattern = t.pattern
            break

    # Feedback lookup
    fb_cur = db.problem_feedback.find(
        {"user_id": user["id"]}, {"_id": 0},
    ).sort("submitted_at", -1)
    all_feedback = await fb_cur.to_list(length=200)
    fb_by_assignment = {}
    for f in all_feedback:
        if f.get("assignment_id"):
            fb_by_assignment[f["assignment_id"]] = f

    # Enrich assignments with problem detail + feedback
    enriched = []
    for a in assignments:
        p = problem_by_id(a["problem_id"])
        if not p:
            continue
        enriched.append({
            **a,
            "problem": p,
            "feedback": fb_by_assignment.get(a["id"]),
        })
    # Sort: unsolved first, then solved
    enriched.sort(key=lambda x: (x["status"] == "solved", x.get("assigned_at", "")))

    # Recent history (last 15 solved/attempted)
    hist_cur = db.problem_assignments.find(
        {"user_id": user["id"], "status": {"$in": ["solved", "attempted"]}}, {"_id": 0},
    ).sort("completed_at", -1).limit(15)
    history_raw = await hist_cur.to_list(length=15)
    history = []
    for h in history_raw:
        p = problem_by_id(h["problem_id"])
        if not p:
            continue
        history.append({**h, "problem": p, "feedback": fb_by_assignment.get(h["id"])})

    return {
        "mission": mission.model_dump(),
        "primary_pattern": primary_pattern,
        "primary_pattern_label": PATTERN_TO_DOMAIN.get(primary_pattern, ("dsa", primary_pattern or "Practice"))[1] if primary_pattern else None,
        "assignments": enriched,
        "history": history,
    }


@router.post("/coding-arena/practice-more")
async def practice_more(payload: dict, user=Depends(get_current_user)):
    """Pick next unseen problem in given (or today's primary) pattern."""
    from server import db
    pattern = payload.get("pattern")
    today = today_date_str()
    mission_doc = await db.daily_missions.find_one({"user_id": user["id"], "date": today})
    if not mission_doc:
        raise HTTPException(status_code=400, detail="No active mission.")
    mission = DailyMission(**_clean(mission_doc))

    if not pattern:
        # infer from today's mission primary DSA task
        for t in mission.tasks:
            if t.kind == "practice" and t.pattern:
                pattern = t.pattern
                break
    if not pattern:
        raise HTTPException(status_code=400, detail="No pattern specified and none inferable.")

    seen_ids = set()
    cur = db.problem_assignments.find(
        {"user_id": user["id"], "pattern": pattern}, {"problem_id": 1, "_id": 0},
    )
    async for row in cur:
        seen_ids.add(row["problem_id"])
    pool = [p for p in problems_by_pattern(pattern) if p["id"] not in seen_ids]
    if not pool:
        raise HTTPException(status_code=404, detail="You've seen every problem in this pattern.")
    chosen = pool[0]

    assignment = ProblemAssignment(
        user_id=user["id"], problem_id=chosen["id"],
        mission_id=mission.id, pattern=pattern, source="practice_more",
    )
    await db.problem_assignments.insert_one(assignment.model_dump())
    await _log_activity(
        db, user["id"], "practice_more",
        f"Extra practice: {chosen['title']}", description=pattern,
    )
    return {"assignment": assignment.model_dump(), "problem": chosen}


# Best-effort mapping from LeetCode Catalog topic tags to Mission Engine
# pattern keys. Used ONLY to route manually-searched practice through the
# existing revision/knowledge pipeline at a sensible granularity — this does
# NOT modify problem_bank.py and does not affect Mission Engine problem
# selection in any way.
_CATALOG_TAG_TO_PATTERN = {
    "array": "arrays", "hash table": "hashing", "two pointers": "two_pointers",
    "sliding window": "sliding_window", "binary search": "binary_search",
    "stack": "stack", "linked list": "linked_list", "tree": "trees",
    "binary tree": "trees", "recursion": "trees", "graph": "graphs",
    "heap (priority queue)": "heap", "dynamic programming": "dp",
    "backtracking": "backtracking", "greedy": "greedy", "string": "strings",
    "bit manipulation": "bit_manipulation", "matrix": "arrays",
}


def _infer_pattern_from_tags(tags: Optional[list]) -> str:
    for t in tags or []:
        key = str(t).strip().lower()
        if key in _CATALOG_TAG_TO_PATTERN:
            return _CATALOG_TAG_TO_PATTERN[key]
    return "arrays"


@router.post("/coding-arena/manual-assignment")
async def create_manual_assignment(payload: dict, user=Depends(get_current_user)):
    """Bridge a manually-searched LeetCode Catalog problem into the existing
    Mission Engine learning workflow (ProblemAssignment -> submit_problem_feedback
    -> Learning Engine -> revision queue) WITHOUT touching problem_bank.py.

    The Catalog remains the sole source of problem metadata for manual search;
    this only creates the minimal ProblemAssignment record the existing
    FeedbackDialog + feedback endpoint already need to operate.
    """
    from server import db
    leetcode_id = payload.get("leetcode_id")
    try:
        leetcode_id = int(leetcode_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="leetcode_id must be an integer")

    problem = catalog_get_by_id(leetcode_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found in catalog")

    pattern = _infer_pattern_from_tags(problem.topic_tags)
    assignment = ProblemAssignment(
        user_id=user["id"], problem_id=f"catalog-{problem.leetcode_id}",
        mission_id=None, pattern=pattern, source="manual_search",
    )
    await db.problem_assignments.insert_one(assignment.model_dump())
    await _log_activity(
        db, user["id"], "practice_more",
        f"Manual search practice: {problem.title}", description=pattern,
    )
    return {
        **assignment.model_dump(),
        "problem": {
            "id": assignment.problem_id,
            "title": problem.title,
            "difficulty": problem.difficulty,
            "estimated_minutes": 30,
            "leetcode_url": problem.url,
            "tags": problem.topic_tags,
        },
        "feedback": None,
    }


@router.post("/coding-arena/assignments/{assignment_id}/feedback")
async def submit_problem_feedback(
    assignment_id: str, payload: ProblemFeedbackPayload, user=Depends(get_current_user),
):
    from server import db
    a = await db.problem_assignments.find_one({"id": assignment_id, "user_id": user["id"]})
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")

    fb = ProblemFeedback(
        user_id=user["id"], problem_id=a["problem_id"],
        assignment_id=assignment_id, mission_id=a.get("mission_id"),
        pattern=a["pattern"], **payload.model_dump(),
    )
    await db.problem_feedback.insert_one(fb.model_dump())

    # Update assignment status
    new_status = "solved" if payload.solved_status != "could_not_solve" else "attempted"
    await db.problem_assignments.update_one(
        {"id": assignment_id},
        {"$set": {"status": new_status, "completed_at": _now_iso(), "notes": payload.notes}},
    )

    # Update knowledge progress based on feedback — writes only to the
    # canonical `knowledge_nodes` collection (no parallel knowledge_progress
    # write; see services/progress_engine.py).
    p = problem_by_id(a["problem_id"])
    progress_node_id = await _assignment_progress_node_id(db, a)
    if progress_node_id:
        # Sync to Roadmap KnowledgeNode (pattern node + track node)
        try:
            from roadmap import CURRENT_VERSION as _V
            targets = {progress_node_id}
            for nid in targets:
                # Confidence is weighted running average with new feedback point
                existing = await db.knowledge_nodes.find_one(
                    {"user_id": user["id"], "roadmap_version": _V, "node_id": nid},
                    {"_id": 0},
                )
                prev_conf = float(existing.get("confidence", 0.0)) if existing else 0.0
                new_conf = round((prev_conf * 3 + payload.confidence) / 4, 2)
                weak = max(0.0, 100 - new_conf * 10)
                mastery = min(100.0, new_conf * 10)
                bucket = "green" if new_conf >= 7 else "yellow" if new_conf >= 4 else "red"
                solved = payload.solved_status != "could_not_solve"
                status = "mastered" if solved and new_conf >= 9 else "completed" if solved else "in_progress"
                await db.knowledge_nodes.update_one(
                    {"user_id": user["id"], "roadmap_version": _V, "node_id": nid},
                    {"$set": {
                        "user_id": user["id"], "roadmap_version": _V, "node_id": nid,
                        "confidence": new_conf, "weakness_score": weak,
                        "mastery_percentage": mastery,
                        "revision_bucket": bucket, "status": status,
                        **({"completion_date": _now_iso()} if solved else {}),
                        "updated_at": _now_iso(),
                    }},
                    upsert=True,
                )
        except Exception:
            pass  # Roadmap sync is best-effort

    # Schedule revision from confidence — canonical Revision Engine, keyed by
    # the track node (same granularity toggle_task uses).
    if progress_node_id:
        await mark_node_for_revision(
            db, user["id"], CURRENT_VERSION, progress_node_id, confidence=payload.confidence,
        )

    # Weakness detection
    if payload.confidence <= 4 or payload.solved_status in ("multi_hints", "could_not_solve"):
        signal = "could_not_solve" if payload.solved_status == "could_not_solve" else \
                 "many_hints" if payload.solved_status == "multi_hints" else "low_confidence"
        w = WeaknessRecord(user_id=user["id"], pattern=a["pattern"], signal=signal)
        await db.weaknesses.insert_one(w.model_dump())

    await _log_activity(
        db, user["id"], "problem_feedback",
        f"Feedback on {(p or {}).get('title', 'problem')}",
        description=f"confidence {payload.confidence}/10 · {payload.solved_status.replace('_',' ')}",
    )
    return {"ok": True, "assignment_id": assignment_id}


# ============ Knowledge tree (drill-down) ============

DOMAIN_ORDER = ["dsa", "java", "lld", "hld", "operating_systems", "dbms", "computer_networks"]


@router.get("/knowledge/tree")
async def get_knowledge_tree(user=Depends(get_current_user)):
    from server import db
    knowledge = await _get_knowledge(db, user["id"])
    onboarding = await _get_onboarding(db, user["id"])
    baseline = (onboarding or {}).get("self_assessment", {})
    by_topic = {k["topic"]: k for k in knowledge}

    # Feedback aggregated by pattern → confidence stats
    fb_cur = db.problem_feedback.find({"user_id": user["id"]}, {"_id": 0})
    all_fb = await fb_cur.to_list(length=500)
    fb_by_pattern = {}
    for f in all_fb:
        fb_by_pattern.setdefault(f["pattern"], []).append(f)

    # Revisions by topic — canonical Revision Engine (services/revision_engine.py)
    revs = await get_revisions_for_user(db, user["id"], CURRENT_VERSION, limit=200, due_only=False)
    rev_by_topic = {}
    for r in revs:
        rev_by_topic.setdefault(r["topic"], []).append(r)
    today = today_date_str()

    tree = []
    for domain in DOMAIN_ORDER:
        # Domain progress
        kp = by_topic.get(domain)
        domain_score = kp["score"] if kp else (baseline.get(domain, 5) * 10)

        # Sub-topics: for DSA come from PATTERN_TO_DOMAIN filtered by domain
        sub_rows = []
        if domain == "dsa":
            for pattern, (d, label) in PATTERN_TO_DOMAIN.items():
                if d != domain:
                    continue
                fbs = fb_by_pattern.get(pattern, [])
                solved = len([f for f in fbs if f["solved_status"] != "could_not_solve"])
                confs = [f["confidence"] for f in fbs]
                avg_conf = round(sum(confs) / len(confs), 1) if confs else None
                # Simple sub-topic progress derived from solved count (max ~10 solved = 100%)
                progress = min(100.0, round(solved * 12.5, 1))
                revision_status = "fresh"
                due_here = [r for r in rev_by_topic.get(domain, []) if r["next_review_date"] <= today]
                if due_here:
                    revision_status = "due"
                elif avg_conf and avg_conf >= 8:
                    revision_status = "mastered"
                sub_rows.append({
                    "pattern": pattern,
                    "label": label,
                    "progress": progress,
                    "problems_solved": solved,
                    "avg_confidence": avg_conf,
                    "revision_status": revision_status,
                })
            sub_rows.sort(key=lambda x: -x["progress"])
        else:
            # For other domains, subtopics come from TOPIC_META
            meta = TOPIC_META.get(domain, {"subtopics": [], "label": domain})
            for sub, _ in meta["subtopics"]:
                sub_rows.append({
                    "pattern": None,
                    "label": sub,
                    "progress": round(domain_score, 1),
                    "problems_solved": 0,
                    "avg_confidence": None,
                    "revision_status": "fresh",
                })

        tree.append({
            "domain": domain,
            "label": TOPIC_META.get(domain, {}).get("label", domain),
            "score": round(domain_score, 1),
            "completions": kp.get("completions", 0) if kp else 0,
            "subtopics": sub_rows,
        })
    return tree


# ============ Company readiness ============

@router.get("/readiness/companies")
async def get_company_readiness(user=Depends(get_current_user)):
    from server import db
    onboarding = await _get_onboarding(db, user["id"])
    if not onboarding:
        return []
    knowledge = await _get_knowledge(db, user["id"])
    target_companies = onboarding.get("target_companies", [])
    # Show target companies first; then all known companies
    known = list(COMPANY_READINESS_WEIGHTS.keys())
    ordered = [c for c in target_companies if c in known] + [c for c in known if c not in target_companies]
    result = []
    for c in ordered:
        result.append({
            "company_id": c,
            "score": compute_company_readiness(c, knowledge, onboarding),
            "is_target": c in target_companies,
        })
    return result


# ============ Aggregated dashboard ============

@router.get("/dashboard")
async def get_dashboard(user=Depends(get_current_user)):
    from server import db
    today = today_date_str()

    onboarding = await _require_onboarding(db, user["id"])

    mission_doc = await db.daily_missions.find_one({"user_id": user["id"], "date": today})
    if not mission_doc:
        await _generate_today_mission(db, user["id"])
        mission_doc = await db.daily_missions.find_one({"user_id": user["id"], "date": today})
    mission = DailyMission(**_clean(mission_doc))

    # Daily login activity (once per day)
    login_today = await db.activity_events.find_one({
        "user_id": user["id"], "kind": "daily_login",
        "ts": {"$gte": f"{today}T00:00:00"},
    })
    if not login_today:
        await _log_activity(db, user["id"], "daily_login", "Signed in")

    knowledge = await _get_knowledge(db, user["id"])
    streak = await _get_streak(db, user["id"])
    readiness = compute_readiness(knowledge, onboarding)
    streak_grid = streak_days_grid(streak)

    revisions = await get_revisions_for_user(db, user["id"], CURRENT_VERSION, limit=6, due_only=False)

    baseline = onboarding.get("self_assessment", {})
    progress_by_topic = {kp["topic"]: kp for kp in knowledge}
    knowledge_view = []
    roadmap = get_roadmap()
    for track_id in roadmap.track_ids():
        kp = progress_by_topic.get(track_id)

        if kp:
            score = kp["score"]
        else:
            score = baseline.get(track_id, 0) * 10

        track = roadmap.get(track_id)
        label = getattr(track, "title", track_id.replace("_", " ").title())

        knowledge_view.append({
            "topic": track_id,
            "label": label,
            "score": round(score, 1),
            "completions": kp.get("completions", 0) if kp else 0,
        })

    # LIMIT to latest 5 activities
    act_cur = db.activity_events.find({"user_id": user["id"]}, {"_id": 0}).sort("ts", -1).limit(5)
    activity = await act_cur.to_list(length=5)

    # Company readiness (targets first, top-6 total)
    target_companies = onboarding.get("target_companies", [])
    company_readiness = []
    known = list(COMPANY_READINESS_WEIGHTS.keys())
    ordered = [c for c in target_companies if c in known] + [c for c in known if c not in target_companies][:5]
    for c in ordered[:6]:
        company_readiness.append({
            "company_id": c,
            "score": compute_company_readiness(c, knowledge, onboarding),
            "is_target": c in target_companies,
        })

    # Latest mission adjustment (sort desc so newest adaptive decision wins)
    adj_cursor = db.mission_adjustments.find(
        {"user_id": user["id"], "for_date": today}, {"_id": 0},
    ).sort("created_at", -1).limit(1)
    adj_list = await adj_cursor.to_list(length=1)
    adj_doc = adj_list[0] if adj_list else None

    # Single source of truth for interview-deadline pacing — the same function
    # the planner/mission generator use — so the UI countdown never drifts.
    pacing_state = compute_pacing_state(
        onboarding.get("interview_target_date"),
        onboarding.get("daily_study_hours"),
    )
    days_to_target = pacing_state["remaining_days"]

    return {
        "today": today,
        "mission": mission.model_dump(),
        "streak": {
            "current": (streak or {}).get("current_streak", 0),
            "longest": (streak or {}).get("longest_streak", 0),
            "last_active_date": (streak or {}).get("last_active_date"),
            "week_grid": streak_grid,
        },
        "readiness": readiness,
        "company_readiness": company_readiness,
        "knowledge": knowledge_view,
        "revisions": revisions,
        "activity": activity,
        "adjustment": adj_doc,
        "onboarding": {
            "target_companies": onboarding.get("target_companies", []),
            "current_position": onboarding.get("current_position"),
            "daily_study_hours": onboarding.get("daily_study_hours"),
            "interview_target_date": onboarding.get("interview_target_date"),
            "estimated_prep_days": onboarding.get("estimated_prep_days"),
            "days_to_target": days_to_target,
        },
        "pacing": {
            "has_target_date": pacing_state["has_target_date"],
            "remaining_days": pacing_state["remaining_days"],
            "pacing_mode": pacing_state["pacing_mode"],
            "label": pacing_state["label"],
            "emoji": pacing_state["emoji"],
        },
    }



# ============ Onboarding patch ============

@router.patch("/onboarding", response_model=OnboardingRecord)
async def patch_onboarding(payload: OnboardingPatch, user=Depends(get_current_user)):
    from server import db
    existing = await db.onboarding.find_one({"user_id": user["id"]})
    if not existing:
        raise HTTPException(status_code=404, detail="Onboarding record not found.")

    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if updates:
        updates["updated_at"] = _now_iso()
        await db.onboarding.update_one({"user_id": user["id"]}, {"$set": updates})
        await _log_activity(
            db, user["id"], "profile_updated", "Mission profile updated",
            description=", ".join(updates.keys()),
        )
        merged = {**existing, **updates}
        assessment_topics = [
            track_id
            for track_id in get_roadmap().track_ids()
            if track_id not in {
                "projects",
                "resume",
                "behavioral",
            }
        ]
        avg_skill = (
            sum(
                merged.get("self_assessment", {}).get(t, 0)
                for t in assessment_topics
            )
            / len(assessment_topics)
        )
        base = 180 - avg_skill * 12
        hours = float(merged.get("daily_study_hours", 2))
        estimated = max(30, int(base * (4.0 / max(hours, 1)) / 2))
        await db.onboarding.update_one(
            {"user_id": user["id"]}, {"$set": {"estimated_prep_days": estimated}},
        )
        today = today_date_str()
        await db.daily_missions.delete_one({
            "user_id": user["id"], "date": today, "status": "in_progress",
        })

    doc = await db.onboarding.find_one({"user_id": user["id"]})
    return OnboardingRecord(**_clean(doc))



# ============ Weekly Activity ============

@router.get("/dashboard/weekly-activity")
async def get_weekly_activity(user=Depends(get_current_user)):
    """Aggregate last-7-day activity by day and by kind.

    Returns a canonical shape that the UI (Mission Control & Analytics) can
    consume without any additional client-side computation. All counts are
    derived from `activity_events` — the same source used by the Notification
    Center and Recent Activity — so numbers are always consistent.
    """
    from server import db

    now = datetime.now(timezone.utc)
    today = now.date()
    start_dt = datetime.combine(today - timedelta(days=6), datetime.min.time(), tzinfo=timezone.utc)

    # Kinds we care about — grouped into user-facing "categories" for the widget.
    # Each activity_event.kind maps to one category.
    kind_to_category = {
        "mission_completed":    "missions",
        "mission_generated":    "missions",
        "task_completed":       "tasks",
        "problem_feedback":     "coding",
        "practice_more":        "coding",
        "topic_completed":      "topics",
        "topic_mastered":       "topics",
        "revision_completed":   "revisions",
        "kb_generated":         "knowledge",
        "kb_regenerated":       "knowledge",
        "mentor_message":       "mentor",
        "mentor_session":       "mentor",
        "confidence_updated":   "confidence",
    }

    # Fetch all activity_events in the last 7 days (single query).
    cursor = db.activity_events.find(
        {
            "user_id": user["id"],
            "ts": {"$gte": start_dt.isoformat()},
        },
        {"_id": 0, "ts": 1, "kind": 1},
    )
    events = await cursor.to_list(length=5000)

    # Bucket by day (YYYY-MM-DD) and by category.
    day_labels = []
    day_keys = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        day_keys.append(d.isoformat())
        day_labels.append(d.strftime("%a"))

    categories = ["missions", "tasks", "coding", "topics", "revisions", "knowledge", "mentor", "confidence"]
    grid = {c: {k: 0 for k in day_keys} for c in categories}
    totals = {c: 0 for c in categories}
    per_day_total = {k: 0 for k in day_keys}

    for e in events:
        ts = e.get("ts")
        kind = e.get("kind")
        cat = kind_to_category.get(kind)
        if not ts or not cat:
            continue
        try:
            day_key = ts[:10]  # ISO date prefix
        except Exception:
            continue
        if day_key not in grid[cat]:
            continue
        grid[cat][day_key] += 1
        totals[cat] += 1
        per_day_total[day_key] += 1

    # Best-effort mentor session count: also include distinct conversations updated in window
    try:
        mentor_conv = db.mentor_conversations.find(
            {"user_id": user["id"], "updated_at": {"$gte": start_dt.isoformat()}},
            {"_id": 0, "updated_at": 1},
        )
        m_events = await mentor_conv.to_list(length=1000)
        for m in m_events:
            day_key = (m.get("updated_at") or "")[:10]
            if day_key and day_key in grid["mentor"]:
                # Counted as a mentor touchpoint on that day
                grid["mentor"][day_key] = max(grid["mentor"][day_key], 1)
        totals["mentor"] = sum(grid["mentor"].values())
    except Exception:
        pass

    # Emit a UI-friendly shape.
    days = [
        {
            "date": day_keys[i],
            "label": day_labels[i],
            "total": per_day_total[day_keys[i]],
            "counts": {c: grid[c][day_keys[i]] for c in categories},
        }
        for i in range(7)
    ]

    max_total = max((d["total"] for d in days), default=0)
    grand_total = sum(totals.values())

    return {
        "range": {"start": day_keys[0], "end": day_keys[-1]},
        "categories": categories,
        "days": days,
        "totals": totals,
        "grand_total": grand_total,
        "max_day_total": max_total,
    }
