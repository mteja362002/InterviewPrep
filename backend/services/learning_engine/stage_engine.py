"""Learning Stage Engine (RC1.3.6A · Phase 3).

The canonical, single-source abstraction for "what stage is this learner at,
in this subject/track". Every other adaptive-engine component (eligibility
engine, candidate generation, ranking, decision trace) should read a
learner's stage state from HERE rather than re-deriving it inline, so this
logic never gets scattered across multiple files.

Reuses existing, already-canonical inputs instead of introducing new ones:
  - `learning_stage` node metadata (foundation < core < intermediate <
    advanced, plus the "interview"/"company_specific" capstone/flat labels)
    already stamped on every roadmap node by
    `scripts/generate_roadmap.py::_infer_learning_stage` — previously pure
    UI/journey-grouping metadata, never read by any engine logic. This module
    is what elevates it to a first-class signal.
  - The SAME `_STAGE_ORDER` / `_node_stage_index` helpers introduced in
    `services/progress_engine.py` for Phase 2's stage-aware onboarding seed
    (imported, not duplicated).
  - `roadmap.get_unlocked_nodes()` (already fixed in Phase 1 to propagate a
    container's prerequisites onto every descendant leaf) for `unlocked_stage`.
  - The `knowledge_nodes` progress rows already loaded by
    `progress_engine.load_user_progress_rows` for confidence/mastery/weakness
    and the `next_revision` field already written by
    `services/revision_engine.py` for revision state — no new collections,
    no new queries.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

from services.progress_engine import _STAGE_ORDER, _node_stage_index, COMPLETED_STATUSES as _COMPLETED_STATUSES


@dataclass
class SubjectLearningState:
    """The canonical per-subject (track) learning state (Phase 3)."""

    track: str
    current_stage: str
    completed_stage: Optional[str]
    unlocked_stage: str
    next_stage: Optional[str]
    current_confidence: float
    current_mastery: float
    current_weakness: float
    revision_state: Dict
    learning_velocity: Optional[float]
    next_eligible_stage: str

    def to_dict(self) -> dict:
        return {
            "track": self.track,
            "current_stage": self.current_stage,
            "completed_stage": self.completed_stage,
            "unlocked_stage": self.unlocked_stage,
            "next_stage": self.next_stage,
            "current_confidence": self.current_confidence,
            "current_mastery": self.current_mastery,
            "current_weakness": self.current_weakness,
            "revision_state": self.revision_state,
            "learning_velocity": self.learning_velocity,
            "next_eligible_stage": self.next_eligible_stage,
        }


def _is_done(node: dict, progress_rows: Dict[str, dict]) -> bool:
    row = progress_rows.get(node["id"]) or {}
    return (row.get("status") or "").lower() in _COMPLETED_STATUSES


def _parse_dt(value) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _revision_state_for_track(nodes: List[dict], progress_rows: Dict[str, dict]) -> dict:
    """Derived purely from the `next_revision` field already written onto
    `knowledge_nodes` rows by services/revision_engine.py::mark_node_for_revision
    — no new collection, no new query."""
    now = datetime.now(timezone.utc)
    due_ids: List[str] = []
    for node in nodes:
        row = progress_rows.get(node["id"]) or {}
        due_at = _parse_dt(row.get("next_revision"))
        if due_at and due_at <= now:
            due_ids.append(node["id"])
    return {"due_count": len(due_ids), "has_due": bool(due_ids), "due_node_ids": due_ids[:5]}


def _learning_velocity(completion_dates: Optional[Iterable]) -> Optional[float]:
    """Nodes completed per day, only when enough history exists (>=2
    completions spanning at least 1 day) — otherwise None, per spec."""
    if not completion_dates:
        return None
    parsed = sorted(dt for dt in (_parse_dt(d) for d in completion_dates) if dt)
    if len(parsed) < 2:
        return None
    span_days = (parsed[-1] - parsed[0]).days
    if span_days <= 0:
        return None
    return round(len(parsed) / span_days, 2)


def _avg(values: List[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def compute_subject_learning_state(
    track: str,
    roadmap,
    progress_rows: Dict[str, dict],
    *,
    completed_ids: Optional[set] = None,
    completion_dates: Optional[Iterable] = None,
) -> SubjectLearningState:
    """Compute the canonical Learning Stage state for one subject (track).

    Pure function over already-loaded data (no DB access), matching the rest
    of services/learning_engine/*. `progress_rows` is the standard
    node_id -> knowledge_nodes-row dict from
    `progress_engine.load_user_progress_rows`.
    """
    nodes = roadmap.get_track_learning_nodes(track)
    if completed_ids is None:
        completed_ids = {
            nid for nid, row in progress_rows.items()
            if (row.get("status") or "").lower() in _COMPLETED_STATUSES
        }

    stage_nodes: Dict[int, List[dict]] = {}
    for node in nodes:
        stage_nodes.setdefault(_node_stage_index(node), []).append(node)

    # Walk the 4 core stages from "foundation" upward to find the highest
    # contiguously-completed prefix (`completed_stage`) and the first
    # not-yet-fully-completed stage (`current_stage`). A stage with zero
    # nodes in this track is trivially satisfied and does not block the walk.
    #
    # RC1.3.7 Phase 6/7 fix: some tracks (e.g. LLD: foundation+core only,
    # then straight to the "interview" case-study capstone) simply have no
    # curriculum authored at "intermediate"/"advanced" — those buckets are
    # empty by curriculum design, not because the learner mastered them.
    # Vacuously walking past empty buckets all the way to the last defined
    # index ("advanced") falsely promoted a learner who only ever completed
    # a track's "core" content straight to "advanced", which then wrongly
    # satisfied the eligibility-widening rule that unlocks the interview
    # capstone for anyone "advanced" (see eligibility._stage_cap_index).
    # `current_stage`/`completed_stage` must never exceed the highest stage
    # index that actually has authored content in this track.
    max_real_stage_idx = max((idx for idx in stage_nodes if idx < len(_STAGE_ORDER)), default=0)
    completed_stage_idx = -1
    current_stage_idx = 0
    for idx in range(len(_STAGE_ORDER)):
        at_stage = stage_nodes.get(idx, [])
        if at_stage and not all(_is_done(n, progress_rows) for n in at_stage):
            current_stage_idx = idx
            break
        completed_stage_idx = idx
        current_stage_idx = idx
        if idx >= max_real_stage_idx:
            break
    else:
        current_stage_idx = len(_STAGE_ORDER) - 1  # every defined stage fully completed
    current_stage_idx = min(current_stage_idx, max(max_real_stage_idx, 0))
    completed_stage_idx = min(completed_stage_idx, max_real_stage_idx)

    completed_stage = _STAGE_ORDER[completed_stage_idx] if completed_stage_idx >= 0 else None
    current_stage = _STAGE_ORDER[current_stage_idx]
    next_stage = (
        _STAGE_ORDER[completed_stage_idx + 1] if completed_stage_idx + 1 < len(_STAGE_ORDER) else None
    )

    # unlocked_stage: reuse the (Phase-1-fixed) prerequisite-propagated
    # get_unlocked_nodes() — the highest core stage with at least one
    # currently-unlockable node in this track.
    unlocked_ids = {n["id"] for n in roadmap.get_unlocked_nodes(completed_ids) if n.get("track") == track}
    unlocked_idx = max(
        (min(_node_stage_index(n), len(_STAGE_ORDER) - 1) for n in nodes if n["id"] in unlocked_ids),
        default=current_stage_idx,
    )
    unlocked_stage = _STAGE_ORDER[unlocked_idx]

    # next_eligible_stage: the immediate next stage, only if it is already
    # reachable through the real prerequisite graph — never skips a stage.
    #
    # RC1.3.7 Phase 6/12 guard: "Foundations First" is a hard governance
    # principle (Persona spec: a learner who has not yet cleared Foundations
    # in a subject must see Foundations only). A track whose "core" module
    # happens to carry no authored prerequisite back onto "foundations"
    # (sparse-graph tracks like OS) would otherwise look trivially
    # "unlocked" and let a still-at-foundation learner skip straight to
    # core content. While still genuinely in the foundation stage, never
    # advance next_eligible_stage past it.
    if current_stage_idx == 0:
        next_eligible_stage = current_stage
    elif current_stage_idx + 1 < len(_STAGE_ORDER):
        candidate_idx = current_stage_idx + 1
        next_eligible_stage = _STAGE_ORDER[candidate_idx] if unlocked_idx >= candidate_idx else current_stage
    else:
        next_eligible_stage = current_stage

    current_stage_nodes = stage_nodes.get(current_stage_idx) or nodes
    confidences, masteries, weaknesses = [], [], []
    for node in current_stage_nodes:
        row = progress_rows.get(node["id"])
        if not row:
            continue
        confidences.append(float(row.get("confidence", 0.0)))
        masteries.append(float(row.get("mastery_percentage", 0.0)))
        weaknesses.append(float(row.get("weakness_score", 0.0)))

    return SubjectLearningState(
        track=track,
        current_stage=current_stage,
        completed_stage=completed_stage,
        unlocked_stage=unlocked_stage,
        next_stage=next_stage,
        current_confidence=_avg(confidences),
        current_mastery=_avg(masteries),
        current_weakness=_avg(weaknesses),
        revision_state=_revision_state_for_track(nodes, progress_rows),
        learning_velocity=_learning_velocity(completion_dates),
        next_eligible_stage=next_eligible_stage,
    )


def compute_all_subject_states(
    roadmap,
    progress_rows: Dict[str, dict],
    *,
    completion_dates_by_track: Optional[Dict[str, Iterable]] = None,
) -> Dict[str, SubjectLearningState]:
    """Compute the Learning Stage state for every roadmap track at once —
    the canonical learning state consumed by the eligibility engine (Phase 4)."""
    completion_dates_by_track = completion_dates_by_track or {}
    completed_ids = {
        nid for nid, row in progress_rows.items()
        if (row.get("status") or "").lower() in _COMPLETED_STATUSES
    }
    return {
        track: compute_subject_learning_state(
            track, roadmap, progress_rows,
            completed_ids=completed_ids,
            completion_dates=completion_dates_by_track.get(track),
        )
        for track in roadmap.track_ids()
    }
