"""Canonical progress engine for roadmap-based learning progress.

This service is the single backend source of truth for roadmap progress. It
derives parent rollups strictly from child progress so that topic, section,
track, and overall progress all remain consistent — and it owns the shared
read/write helpers (`load_user_progress_rows`, `score_to_node_fields`) so
every consumer (Mission Engine, Roadmap API, AI Mentor) reads and writes the
same `knowledge_nodes` collection the same way.
"""
from __future__ import annotations

from typing import Dict, Iterable, Optional


# ---------------------------------------------------------------------------
# Canonical status vocabulary — import from here, never redefine.
# ---------------------------------------------------------------------------

# Statuses that mean the learner has "done" this node at least once.
# Use this for eligibility gating, prerequisite checks, and rollup counting.
COMPLETED_STATUSES = frozenset({"completed", "mastered", "revision_due"})

# Subset: truly done (no pending revision). Use for strict "is this finished?"
# checks like remaining-curriculum counts.
DONE_STATUSES = frozenset({"completed", "mastered"})


def _normalize_status(raw: Optional[str]) -> str:
    return raw or "not_started"


def _aggregate_progress(roadmap, progress_rows: Optional[Dict[str, dict]] = None) -> Dict[str, dict]:
    """Return canonical progress rollups keyed by roadmap node id."""
    progress_rows = progress_rows or {}
    cache: Dict[str, dict] = {}

    def _leaf_topic_count(node_id: str) -> int:
        node = roadmap.get(node_id)
        if not node:
            return 0
        children = roadmap.children(node_id)
        if not children:
            return 1
        return sum(_leaf_topic_count(child["id"]) for child in children)

    def _rollup(node_id: str) -> dict:
        if node_id in cache:
            return cache[node_id]

        node = roadmap.get(node_id)
        if not node:
            return {
                "status": "not_started",
                "confidence": 0.0,
                "weakness_score": 0.0,
                "mastery_percentage": 0.0,
                "total_topics": 0,
                "completed_topics": 0,
                "remaining_topics": 0,
                "completion_pct": 0.0,
                "estimated_hours_remaining": 0.0,
            }

        children = roadmap.children(node_id)
        direct = progress_rows.get(node_id)
        # A progress row keyed at this node id only represents true leaf-level
        # progress when the node has no children. Legacy per-track progress rows
        # (node_id == track id) must fall through to the structural rollup below
        # instead of collapsing a non-leaf node's total_topics to 1.
        if direct and not children:
            status = _normalize_status(direct.get("status"))
            confidence = float(direct.get("confidence", 0.0))
            weakness = float(direct.get("weakness_score", 0.0))
            mastery = float(direct.get("mastery_percentage", 0.0))
            total_topics = 1
            completed_topics = 1 if status in {"completed", "mastered"} else 0
            remaining_topics = total_topics - completed_topics
            completion_pct = 100.0 if completed_topics else 0.0
            result = {
                "status": status,
                "confidence": round(confidence, 2),
                "weakness_score": round(weakness, 2),
                "mastery_percentage": round(mastery, 2),
                "total_topics": total_topics,
                "completed_topics": completed_topics,
                "remaining_topics": remaining_topics,
                "completion_pct": completion_pct,
                "estimated_hours_remaining": 0.0,
            }
            cache[node_id] = result
            return result

        child_rollups = [_rollup(child["id"]) for child in children]
        total_topics = _leaf_topic_count(node_id)
        completed_topics = sum(r["completed_topics"] for r in child_rollups)
        remaining_topics = total_topics - completed_topics
        completion_pct = round((completed_topics / total_topics) * 100.0, 2) if total_topics else 0.0

        if not child_rollups:
            result = {
                "status": "not_started",
                "confidence": 0.0,
                "weakness_score": 0.0,
                "mastery_percentage": 0.0,
                "total_topics": 1,
                "completed_topics": 0,
                "remaining_topics": 1,
                "completion_pct": 0.0,
                "estimated_hours_remaining": 0.0,
            }
            cache[node_id] = result
            return result

        any_progress = any(r["status"] != "not_started" for r in child_rollups)
        # A parent is only "completed" when EVERY child is completed/mastered.
        # Do NOT filter out not_started children before this check — doing so
        # made a single completed child (out of many untouched siblings)
        # vacuously satisfy all(), misreporting the whole parent as "completed".
        all_completed = all(r["status"] in {"completed", "mastered"} for r in child_rollups)
        status = "completed" if all_completed else "in_progress" if any_progress else "not_started"
        avg_conf = sum(r["confidence"] for r in child_rollups) / len(child_rollups) if child_rollups else 0.0
        avg_mastery = sum(r["mastery_percentage"] for r in child_rollups) / len(child_rollups) if child_rollups else 0.0
        avg_weak = sum(r["weakness_score"] for r in child_rollups) / len(child_rollups) if child_rollups else 0.0
        result = {
            "status": status,
            "confidence": round(avg_conf, 2),
            "weakness_score": round(avg_weak, 2),
            "mastery_percentage": round(avg_mastery, 2),
            "total_topics": total_topics,
            "completed_topics": completed_topics,
            "remaining_topics": remaining_topics,
            "completion_pct": completion_pct,
            "estimated_hours_remaining": 0.0,
        }
        cache[node_id] = result
        return result

    def _initial_root_ids() -> list[str]:
        root = roadmap.get("root") if hasattr(roadmap, "get") else None
        if root:
            return [root["id"]]

        tracks = getattr(roadmap, "tracks", None)
        if callable(tracks):
            track_nodes = tracks()
            if track_nodes:
                return [track["id"] for track in track_nodes if track]

        return []

    for node_id in _initial_root_ids():
        _rollup(node_id)

    # Walk every reachable node so parent rollups exist for the whole tree.
    seen = set()
    stack = [roadmap.get(node_id) for node_id in _initial_root_ids() if roadmap.get(node_id)]
    while stack:
        node = stack.pop()
        node_id = node["id"]
        if node_id in seen:
            continue
        seen.add(node_id)
        _rollup(node_id)
        stack.extend(roadmap.children(node_id))

    return cache


def build_canonical_progress(roadmap, progress_rows=None, onboarding=None):
    """Certified actual rollups with separate, explicitly unverified legacy views.

    Aggregation math is unchanged. Only the admissible evidence population changes.
    Onboarding is a subject declaration, never a topic completion projection here.
    """
    from services.evidence import actual_row, legacy_fields, LEGACY
    rows = progress_rows or {}
    actual = _aggregate_progress(roadmap, {nid: actual_row({**row, "node_id": nid}, roadmap) for nid, row in rows.items()})
    legacy_rows = {nid: legacy_fields(row) for nid, row in rows.items() if legacy_fields(row)}
    legacy = _aggregate_progress(roadmap, legacy_rows)
    baseline = (onboarding or {}).get("self_assessment") or {}
    # Only authored onboarding fields are declarations; independent tracks have none.
    from models import OnboardingSelfAssessment
    baseline = {key: float(value) * 10 for key, value in baseline.items()
                if key in OnboardingSelfAssessment.model_fields}
    for nid, roll in actual.items():
        node = roadmap.get(nid) or {}
        track = node.get("track") or nid
        roll["metric_basis"] = "certified_actual"
        roll["onboarding_baseline"] = baseline.get(track)
        # Include a legacy aggregate only when a descendant actually has stored state.
        stack = [nid]
        has_legacy = False
        while stack:
            child_id = stack.pop()
            if child_id in legacy_rows:
                has_legacy = True
                break
            stack.extend(child["id"] for child in roadmap.children(child_id))
        roll["legacy_progress"] = ({**legacy.get(nid, {}), "classification": LEGACY,
                                    "stored_fields": legacy_rows.get(nid)} if has_legacy else None)
    return actual


def count_remaining_learning_nodes(roadmap, progress_rows: Dict[str, dict]) -> int:
    """Count roadmap learning nodes not yet completed/mastered.

    This is the "remaining_curriculum" input to the pacing engine
    (services/learning_engine/pacing.py) — kept here alongside the other
    canonical `knowledge_nodes` readers rather than duplicated per caller.
    """
    remaining = 0
    for node in roadmap.get_learning_nodes():
        row = progress_rows.get(node["id"])
        if not row or row.get("status") not in DONE_STATUSES:
            remaining += 1
    return remaining


async def load_user_progress_rows(db, user_id: str, roadmap_version=None) -> Dict[str, dict]:
    """Canonical loader for a user's `knowledge_nodes` rows, keyed by node_id.

    Single shared query used by every consumer (Roadmap API, Mission Engine,
    dashboard readiness) instead of each route module querying the collection
    independently.
    """
    from roadmap import CURRENT_VERSION
    version = roadmap_version or CURRENT_VERSION
    cur = db.knowledge_nodes.find({"user_id": user_id}, {"_id": 0})
    docs = await cur.to_list(length=2000)
    # A missing version cannot safely be assigned to the current curriculum.
    return {d["node_id"]: d for d in docs if d.get("roadmap_version") == version}


def score_to_node_fields(score: float) -> dict:
    """Convert a 0-100 mastery-style score into derived KnowledgeNode fields.

    Single canonical mapping (confidence / weakness_score / revision_bucket /
    status) replacing the near-identical inline conversions that used to be
    duplicated across the migration in server.py and the feedback-sync path
    in routes_missions.py.
    """
    score = max(0.0, min(100.0, score))
    confidence = round(score / 10.0, 2)
    weakness = round(max(0.0, 100.0 - score), 2)
    bucket = "green" if confidence >= 7 else "yellow" if confidence >= 4 else "red"
    status = "mastered" if confidence >= 9 else "in_progress" if score > 0 else "not_started"
    return {
        "confidence": confidence,
        "mastery_percentage": round(score, 2),
        "weakness_score": weakness,
        "revision_bucket": bucket,
        "status": status,
    }


def confidence_to_node_fields(confidence: float) -> dict:
    """Convert a 0-10 confidence value into derived KnowledgeNode fields.

    Canonical inverse of ``score_to_node_fields`` for call-sites that
    receive a confidence rating (e.g. the confidence slider endpoint,
    coding-feedback sync) rather than a 0-100 mastery score. Both
    functions produce the exact same field set so callers can use them
    interchangeably.
    """
    mastery = min(100.0, max(0.0, confidence) * 10.0)
    return score_to_node_fields(mastery)


# RC1.3.6A — Phase 2: stage-aware onboarding seeding.
#
# `learning_stage` (foundation < core < intermediate < advanced) is stamped
# on every roadmap learning node by scripts/generate_roadmap.py, purely as a
# UI/journey-grouping label previously never read by any engine logic. This
# is now the canonical scale a track's onboarding rating is projected onto.
_STAGE_ORDER = ("foundation", "core", "intermediate", "advanced")

# A track whose learning nodes are NOT structured along `_STAGE_ORDER` (every
# node instead carries the flat "company_specific" fallback stage — the
# behavioral/projects/resume tracks) has no stage progression to project a
# rating onto, so it keeps the old flat/uniform baseline behavior.
_UNDERSTOOD_BASELINE_SCORE = 85.0  # solid, deliberately not "mastered" (>=90)
_NEUTRAL_BASELINE_RATING = 5.0

# Curriculum Sync Phase 3: which tracks must NEVER receive an inherited or
# default onboarding baseline is derived from the roadmap's own
# `subject_prerequisites` DAG metadata (roadmap.subjects_without_prerequisites())
# rather than a hardcoded track-id list. That set is exactly: the true root
# of the academic chain (Programming Fundamentals — the universal starting
# point, earned only by actually studying it) plus every subject deliberately
# isolated from the DAG (Projects, Resume & LinkedIn, Behavioral — the
# onboarding sliders never ask about these, so they must start at a genuine
# 0% too, never a neutral/default "5" baseline).


def _stage_for_rating(rating: float) -> str:
    """Deterministic onboarding-rating -> starting-stage mapping.

    A track's 1-10 self-assessment slider no longer stamps one identical
    confidence value onto every node in the track — it selects the STAGE
    the learner is presumed to already stand at: rating=1 lands at
    "foundation" (only Arrays/Strings/Complexity-style nodes are seeded as
    understood), rating=8 lands at "advanced" (foundation/core/intermediate
    nodes are additionally marked understood so advanced nodes become
    legitimately eligible instead of everything getting one flat value).
    """
    if rating <= 2:
        return "foundation"
    if rating <= 4:
        return "core"
    if rating <= 6:
        return "intermediate"
    return "advanced"


def _node_stage_index(node: dict) -> int:
    stage = node.get("learning_stage")
    if stage in _STAGE_ORDER:
        return _STAGE_ORDER.index(stage)
    # "interview" (LLD/HLD case-study capstones) and "company_specific"
    # (behavioral/projects/resume) sit beyond the 4 core stages and are
    # never auto-marked understood by onboarding alone — they're earned by
    # completing the stage progression, not granted from a slider.
    return len(_STAGE_ORDER)


def onboarding_planner_projection(self_assessment, roadmap):
    """Existing stage projection, runtime only. Never persisted or actual evidence.

    Retains the authored stage ordering and root treatment for planner compatibility.
    PF prerequisite credit still comes from effective knowledge, exactly as before.
    """
    rows = {}
    self_assessment = self_assessment or {}
    root_subjects = set(roadmap.root_subject_ids())
    isolated_subjects = set(roadmap.subjects_without_prerequisites()) - root_subjects
    for track in roadmap.track_ids():
        if track in root_subjects:
            continue  # never pre-seeded — see root_subjects above
        rating = self_assessment.get(track)
        if rating is None:
            rating = 0.0 if track in isolated_subjects else _NEUTRAL_BASELINE_RATING
        rating = max(0.0, min(10.0, float(rating)))
        nodes = roadmap.get_track_learning_nodes(track)
        is_staged_track = any(node.get("learning_stage") in _STAGE_ORDER for node in nodes)
        starting_index = _STAGE_ORDER.index(_stage_for_rating(rating)) if is_staged_track else -1

        for node in nodes:
            node_id = node["id"]

            if not is_staged_track:
                # Flat track (behavioral/projects/resume): uniform baseline —
                # genuine 0%/not_started when no explicit rating was given,
                # otherwise the prior "in_progress" proportional baseline.
                fields = score_to_node_fields(rating * 10.0)
                fields["status"] = "in_progress" if rating > 0 else "not_started"
            else:
                node_index = _node_stage_index(node)
                if node_index > starting_index:
                    continue  # above the learner's starting stage — cold start, no row
                if node_index < starting_index:
                    fields = score_to_node_fields(_UNDERSTOOD_BASELINE_SCORE)
                    fields["status"] = "completed"  # legitimately satisfies downstream prerequisites
                else:
                    fields = score_to_node_fields(rating * 10.0)
                    fields["status"] = "in_progress"  # never "mastered" from a slider alone

            rows[node_id] = {
                "node_id": node_id,
                "roadmap_version": roadmap.version,
                **fields,
                "planner_progress_source": "onboarding_baseline",
            }
    return rows


async def seed_knowledge_nodes_from_self_assessment(db, user_id, self_assessment, roadmap):
    """Compatibility entry point: baseline lives in onboarding, never knowledge_nodes.

    Planner stage inputs are supplied by onboarding_planner_projection at runtime.
    No historical or certified row is overwritten on onboarding updates.
    """
    return 0


def planner_progress_rows(roadmap, rows, onboarding):
    """Apply the former seed only at the planner boundary, not to evidence readers."""
    from services.evidence import planner_row
    scores = (onboarding or {}).get("self_assessment")
    progress = onboarding_planner_projection(scores, roadmap) if scores is not None else {}
    progress.update({row["node_id"]: planner_row(row) for row in rows if row.get("node_id")})
    return list(progress.values())
