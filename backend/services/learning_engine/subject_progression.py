"""Curriculum Progression Engine — Subject Learning Sessions & Scheduling.

The engine that transforms PrepOS from a flat unlock-based roadmap viewer
into a guided educational journey.  Every public function is a **pure
function** over already-loaded data — no DB access, no side effects,
deterministic (same inputs → same output).

Architecture:
    Roadmap (data)  →  This module (educational decisions)  →  Planner (thin orchestrator)

Key concepts:
    - SubjectLearningSession: complete educational state of one learner
      within one subject (not a cursor — carries lifecycle, mastery,
      scheduling signals, and the next recommended action).
    - LearnerGoal: domain-agnostic curriculum objective that scopes
      which subjects are required and at what depth.
    - Topic Lifecycle: locked → learning → practice → revision →
      assessment → mastered (with graceful degradation for study-only topics).
    - Subject Status: locked → eligible → active → paused → completed → mastered.
    - Subject Bundles: derived from roadmap DAG, not hardcoded.
    - Mission Explanation Engine: deterministic human-readable reasons
      for every scheduling decision.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

from services.progress_engine import COMPLETED_STATUSES as _COMPLETED_STATUSES
_MASTERED_STATUSES = frozenset({"completed", "mastered"})

# Fairness constants
MAX_CONSECUTIVE_SUBJECT_DAYS = 3
MIN_REPRESENTATION_WINDOW = 5  # days


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class LearnerGoal:
    """The learner's overarching curriculum objective.

    Domain-agnostic: scopes which subjects are required and at what
    depth.  Does NOT encode any domain-specific semantics — those are
    emergent from the roadmap content and the learner's own context.

    v1: A single implicit default goal derived from the roadmap.
    v2+: User-configurable goals with different track subsets.
    """
    goal_id: str
    label: str
    required_track_ids: List[str]
    required_depth: str  # "core" | "advanced" | "mastered"
    timeline_days: Optional[int] = None

    # ---- Derived mastery -------------------------------------------------
    mastery_pct: float = 0.0
    subjects_completed: int = 0
    subjects_total: int = 0


@dataclass
class LearningVelocity:
    """Velocity metrics for one subject.  Computed in v1, consumed in v2+.

    All fields are Optional — None means insufficient data to compute.
    """
    nodes_per_day: Optional[float] = None
    days_per_topic: Optional[float] = None
    days_per_module: Optional[float] = None
    velocity_trend: Optional[str] = None  # "accelerating"|"steady"|"decelerating"


@dataclass
class SubjectLearningSession:
    """The complete educational state of a learner within one subject."""

    # ---- Identity --------------------------------------------------------
    track_id: str
    track_label: str

    # ---- Subject status --------------------------------------------------
    status: str  # locked|eligible|active|paused|completed|mastered

    # ---- Current position ------------------------------------------------
    current_module_id: Optional[str] = None
    current_module_label: Optional[str] = None
    current_topic_id: Optional[str] = None
    current_topic_label: Optional[str] = None
    current_node_id: Optional[str] = None
    current_node_label: Optional[str] = None

    # ---- Topic lifecycle -------------------------------------------------
    topic_lifecycle: str = "locked"

    # ---- Progress --------------------------------------------------------
    progress_pct: float = 0.0
    completed_nodes: int = 0
    total_nodes: int = 0

    # ---- Session signals -------------------------------------------------
    has_revision_due: bool = False
    has_assessment_due: bool = False
    last_activity_date: Optional[str] = None
    days_since_activity: Optional[int] = None
    consecutive_days_scheduled: int = 0

    # ---- Next recommendation ---------------------------------------------
    next_node_id: Optional[str] = None
    next_activity_type: Optional[str] = None  # study|coding|quiz
    next_cta: Optional[str] = None  # open_knowledge_base|open_coding_arena|start_assessment

    # ---- Completion condition --------------------------------------------
    remaining_in_topic: int = 0
    remaining_in_module: int = 0

    # ---- Multi-level mastery (§19) ---------------------------------------
    module_mastery: Optional[dict] = None
    subject_mastery_info: Optional[dict] = None

    # ---- Future extensibility (v1 defaults) ------------------------------
    confidence_score: Optional[float] = None
    spaced_repetition_due: Optional[str] = None
    streak_days: Optional[int] = None
    ai_mentor_suggestion: Optional[str] = None
    learning_velocity: Optional[LearningVelocity] = None


@dataclass
class TaskPlan:
    """One task within the daily learning plan."""
    session: SubjectLearningSession
    node_id: str
    activity_type: str
    cta: str
    reason_code: str
    explanation: str
    continuity_context: str = ""
    lifecycle_position: str = ""


@dataclass
class DailyLearningPlan:
    """Internal representation — maps to existing DailyMission fields."""
    date: str
    selected_sessions: List[SubjectLearningSession] = field(default_factory=list)
    task_plans: List[TaskPlan] = field(default_factory=list)
    plan_narrative: str = ""
    plan_insight: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Subject status derivation (§3)
# ---------------------------------------------------------------------------

def _derive_subject_status(
    track_id: str,
    subject_prereqs: List[str],
    completed_subjects: Set[str],
    track_nodes: List[dict],
    progress_map: Dict[str, dict],
) -> str:
    """Derive the six-state subject status.  Pure function."""
    # Gate 1: subject prerequisites
    if subject_prereqs and not all(sp in completed_subjects for sp in subject_prereqs):
        return "locked"

    # Gate 1.5: effective completion (planner-only).
    # When the planner's unified completed_subjects set already contains
    # this track (via actual node completion OR onboarding-derived
    # effective knowledge), treat it as "completed" for scheduling
    # purposes.  This prevents the session pipeline from serving
    # entry-level nodes on a track the learner has declared mastery of.
    #
    # We still distinguish "completed" from "mastered": mastered requires
    # every node actually done.  The effective-completion path can only
    # produce "completed" because no actual nodes have been touched.
    if track_id in completed_subjects:
        all_done = all(
            (progress_map.get(n["id"], {}).get("status") or "").lower()
            in _COMPLETED_STATUSES
            for n in track_nodes
        )
        return "mastered" if all_done else "completed"

    # Gate 2: any progress at all?
    has_progress = any(
        (progress_map.get(n["id"], {}).get("status") or "").lower()
        not in ("", "not_started")
        for n in track_nodes
    )
    if not has_progress:
        return "eligible"

    # Gate 3: foundation + core completion
    fc_nodes = [
        n for n in track_nodes
        if n.get("learning_stage") in ("foundation", "core", None)
    ]
    fc_done = all(
        (progress_map.get(n["id"], {}).get("status") or "").lower() in _COMPLETED_STATUSES
        for n in fc_nodes
    ) if fc_nodes else False

    if not fc_done:
        return "active"

    # Gate 4: all nodes done?
    all_done = all(
        (progress_map.get(n["id"], {}).get("status") or "").lower() in _COMPLETED_STATUSES
        for n in track_nodes
    )
    return "mastered" if all_done else "completed"


# ---------------------------------------------------------------------------
# Topic lifecycle derivation (§5)
# ---------------------------------------------------------------------------

def _infer_topic_lifecycle(
    node: dict,
    progress_map: Dict[str, dict],
) -> str:
    """Derive the topic lifecycle state for one learning node.

    Graceful degradation: study-only nodes skip practice/assessment.
    """
    node_id = node.get("id", "")
    row = progress_map.get(node_id, {})
    status = (row.get("status") or "").lower()
    activity_type = node.get("activity_type", "study")

    # Already done?
    if status in _MASTERED_STATUSES:
        return "mastered"

    # Revision due?
    if status == "revision_due":
        return "revision"

    # Not yet started?
    if status in ("", "not_started"):
        return "learning"

    # In-progress — determine based on activity type
    if activity_type == "coding":
        # Has the learner studied already? (check kb_viewed or study marker)
        kb_viewed = row.get("kb_viewed") or row.get("study_completed")
        if not kb_viewed:
            return "learning"
        # Has practice been attempted?
        practice_attempts = row.get("practice_attempts") or row.get("problems_attempted") or 0
        if isinstance(practice_attempts, (int, float)) and practice_attempts > 0:
            return "revision"
        return "practice"

    # Study-only: simple two-state (learning → mastered)
    return "learning"


def _lifecycle_to_activity(lifecycle: str, node: dict) -> Tuple[str, str]:
    """Map lifecycle state to (activity_type, cta)."""
    mapping = {
        "learning": ("study", "open_knowledge_base"),
        "practice": ("coding", "open_coding_arena"),
        "revision": ("study", "open_knowledge_base"),
        "assessment": ("quiz", "start_assessment"),
    }
    return mapping.get(lifecycle, ("study", "open_knowledge_base"))


# ---------------------------------------------------------------------------
# Subject bundles — derived from roadmap DAG (§17)
# ---------------------------------------------------------------------------

def derive_subject_bundles(roadmap) -> Dict[str, Dict]:
    """Derive subject bundles from the roadmap's dependency graph.

    Grouping rule: tracks with identical subject_prerequisites form
    a natural bundle.  Fully data-driven — adding a new track to the
    roadmap automatically places it in the correct bundle.
    """
    bundles: Dict[str, List[str]] = {}
    for track in roadmap.tracks():
        track_id = track["id"]
        prereqs = tuple(sorted(track.get("subject_prerequisites") or []))
        bundle_key = "_".join(prereqs) if prereqs else "roots"
        bundles.setdefault(bundle_key, []).append(track_id)
    return {
        key: {"tracks": tracks, "scheduling_weight": 1.0}
        for key, tracks in bundles.items()
    }


def _bundle_for_track(track_id: str, bundles: Dict[str, Dict]) -> Optional[str]:
    """Return the bundle key that contains the given track."""
    for key, bundle in bundles.items():
        if track_id in bundle["tracks"]:
            return key
    return None


# ---------------------------------------------------------------------------
# Multi-level mastery (§19)
# ---------------------------------------------------------------------------

def _is_node_mastered(node: dict, progress_map: Dict[str, dict]) -> bool:
    status = (progress_map.get(node["id"], {}).get("status") or "").lower()
    return status in _MASTERED_STATUSES


def compute_module_mastery(
    module_id: str,
    track_nodes: List[dict],
    progress_map: Dict[str, dict],
) -> dict:
    """Compute mastery for one module.  Pure derived state."""
    module_nodes = [n for n in track_nodes if n.get("module_id") == module_id]
    mastered = [n for n in module_nodes if _is_node_mastered(n, progress_map)]
    total = len(module_nodes)
    return {
        "module_id": module_id,
        "mastery_pct": (len(mastered) / total * 100) if total else 0.0,
        "is_mastered": len(mastered) == total and total > 0,
        "completed": len(mastered),
        "total": total,
    }


def compute_subject_mastery(
    track_id: str,
    track_nodes: List[dict],
    progress_map: Dict[str, dict],
) -> dict:
    """Compute mastery for one subject.  Pure derived state."""
    mastered = [n for n in track_nodes if _is_node_mastered(n, progress_map)]
    fc_nodes = [
        n for n in track_nodes
        if n.get("learning_stage") in ("foundation", "core", None)
    ]
    fc_mastered = [n for n in fc_nodes if _is_node_mastered(n, progress_map)]
    total = len(track_nodes)
    fc_total = len(fc_nodes)
    return {
        "track_id": track_id,
        "overall_pct": (len(mastered) / total * 100) if total else 0.0,
        "core_pct": (len(fc_mastered) / fc_total * 100) if fc_total else 0.0,
        "is_core_mastered": len(fc_mastered) == fc_total and fc_total > 0,
        "is_fully_mastered": len(mastered) == total and total > 0,
    }


def compute_goal_mastery(
    goal: LearnerGoal,
    all_subject_mastery: Dict[str, dict],
) -> dict:
    """Compute mastery for a goal.  Pure derived state."""
    required = [all_subject_mastery.get(t, {}) for t in goal.required_track_ids]
    core_done = sum(1 for s in required if s.get("is_core_mastered"))
    total = len(required)
    return {
        "goal_id": goal.goal_id,
        "mastery_pct": sum(s.get("core_pct", 0) for s in required) / total if total else 0.0,
        "subjects_mastered": core_done,
        "subjects_total": total,
        "is_goal_achieved": core_done == total and total > 0,
    }


# ---------------------------------------------------------------------------
# Learning velocity (§20) — computed in v1, unused by scheduling
# ---------------------------------------------------------------------------

def compute_learning_velocity(
    track_nodes: List[dict],
    progress_map: Dict[str, dict],
) -> LearningVelocity:
    """Derive velocity from completion timestamps in knowledge_nodes.

    Uses existing ``completed_at`` / ``updated_at`` fields.
    Returns a LearningVelocity with None fields when insufficient data.
    """
    completion_dates: List[str] = []
    for n in track_nodes:
        row = progress_map.get(n["id"], {})
        ts = row.get("completed_at") or row.get("updated_at")
        if ts and (row.get("status") or "").lower() in _COMPLETED_STATUSES:
            completion_dates.append(str(ts)[:10])  # YYYY-MM-DD

    if len(completion_dates) < 2:
        return LearningVelocity()

    unique_days = sorted(set(completion_dates))
    total_completed = len(completion_dates)
    day_span = max(1, len(unique_days))
    nodes_per_day = total_completed / day_span

    return LearningVelocity(
        nodes_per_day=round(nodes_per_day, 2),
        days_per_topic=round(day_span / max(1, total_completed), 2),
    )


# ---------------------------------------------------------------------------
# Build one Subject Learning Session (§4)
# ---------------------------------------------------------------------------

def build_subject_learning_session(
    track_id: str,
    roadmap,
    completed_subjects: Set[str],
    progress_map: Dict[str, dict],
) -> SubjectLearningSession:
    """Build the complete learning session for one subject.

    Pure function over already-loaded data.  No DB access.
    Deterministic: same inputs -> same session.
    """
    track = roadmap.get(track_id)
    if not track:
        return SubjectLearningSession(
            track_id=track_id, track_label=track_id, status="locked",
        )

    track_label = track.get("label", track_id)
    track_nodes = roadmap.get_track_learning_nodes(track_id)
    subject_prereqs = track.get("subject_prerequisites") or []

    # Derive subject status
    status = _derive_subject_status(
        track_id, subject_prereqs, completed_subjects, track_nodes, progress_map,
    )

    # If locked, return minimal session
    if status == "locked":
        return SubjectLearningSession(
            track_id=track_id, track_label=track_label, status="locked",
            total_nodes=len(track_nodes),
        )

    # Count completed nodes for progress
    completed_count = sum(
        1 for n in track_nodes
        if (progress_map.get(n["id"], {}).get("status") or "").lower() in _COMPLETED_STATUSES
    )
    total = len(track_nodes)
    progress_pct = (completed_count / total * 100) if total else 0.0

    # Revision/assessment signals
    has_revision_due = any(
        (progress_map.get(n["id"], {}).get("status") or "").lower() == "revision_due"
        for n in track_nodes
    )

    # Last activity date
    last_activity = None
    days_since = None
    for n in track_nodes:
        row = progress_map.get(n["id"], {})
        ts = row.get("completed_at") or row.get("updated_at")
        if ts:
            ts_str = str(ts)[:10]
            if last_activity is None or ts_str > last_activity:
                last_activity = ts_str
    if last_activity:
        try:
            last_dt = datetime.strptime(last_activity, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            days_since = (datetime.now(timezone.utc) - last_dt).days
        except (ValueError, TypeError):
            pass

    # Walk modules in authored order to find first incomplete topic
    current_module_id = None
    current_module_label = None
    current_topic_id = None
    current_topic_label = None
    current_node_id = None
    current_node_label = None
    lifecycle = "mastered"
    remaining_topic = 0
    remaining_module = 0

    modules = track.get("modules") or []
    found = False
    for module in modules:
        mod_id = module.get("id")
        mod_label = module.get("label", mod_id)
        topics = module.get("topics") or []
        mod_nodes = [n for n in track_nodes if n.get("module_id") == mod_id]

        for topic in topics:
            topic_id = topic.get("id")
            topic_label = topic.get("label", topic_id)
            # Find learning nodes for this topic
            topic_nodes = [n for n in track_nodes if n.get("topic_id") == topic_id]
            if not topic_nodes:
                # Some topics may be structural (subtopic containers)
                # Try matching by id prefix
                topic_nodes = [
                    n for n in track_nodes
                    if n["id"].startswith(topic_id + ".") or n["id"] == topic_id
                ]

            # Check if this topic is complete
            all_mastered = all(
                (progress_map.get(n["id"], {}).get("status") or "").lower() in _MASTERED_STATUSES
                for n in topic_nodes
            ) if topic_nodes else True

            if not all_mastered and not found:
                # This is the first incomplete topic — the current session
                found = True
                current_module_id = mod_id
                current_module_label = mod_label
                current_topic_id = topic_id
                current_topic_label = topic_label

                # Find the first incomplete node within this topic
                for n in topic_nodes:
                    n_status = (progress_map.get(n["id"], {}).get("status") or "").lower()
                    if n_status not in _MASTERED_STATUSES:
                        current_node_id = n["id"]
                        current_node_label = n.get("label", n["id"])
                        lifecycle = _infer_topic_lifecycle(n, progress_map)
                        break

                remaining_topic = sum(
                    1 for n in topic_nodes
                    if (progress_map.get(n["id"], {}).get("status") or "").lower()
                    not in _MASTERED_STATUSES
                )
                remaining_module = sum(
                    1 for n in mod_nodes
                    if (progress_map.get(n["id"], {}).get("status") or "").lower()
                    not in _MASTERED_STATUSES
                )
                break
        if found:
            break

    # Determine next action
    next_node_id = current_node_id
    if current_node_id:
        next_activity, next_cta = _lifecycle_to_activity(
            lifecycle, roadmap.get(current_node_id) or {},
        )
    else:
        next_activity, next_cta = "study", "open_knowledge_base"

    # Mastery data
    subj_mastery = compute_subject_mastery(track_id, track_nodes, progress_map)
    mod_mastery = (
        compute_module_mastery(current_module_id, track_nodes, progress_map)
        if current_module_id else None
    )

    # Velocity
    velocity = compute_learning_velocity(track_nodes, progress_map)

    return SubjectLearningSession(
        track_id=track_id,
        track_label=track_label,
        status=status,
        current_module_id=current_module_id,
        current_module_label=current_module_label,
        current_topic_id=current_topic_id,
        current_topic_label=current_topic_label,
        current_node_id=current_node_id,
        current_node_label=current_node_label,
        topic_lifecycle=lifecycle,
        progress_pct=round(progress_pct, 1),
        completed_nodes=completed_count,
        total_nodes=total,
        has_revision_due=has_revision_due,
        has_assessment_due=False,  # v1: no assessment gate enforcement
        last_activity_date=last_activity,
        days_since_activity=days_since,
        next_node_id=next_node_id,
        next_activity_type=next_activity,
        next_cta=next_cta,
        remaining_in_topic=remaining_topic,
        remaining_in_module=remaining_module,
        module_mastery=mod_mastery,
        subject_mastery_info=subj_mastery,
        learning_velocity=velocity,
    )


# ---------------------------------------------------------------------------
# Build all sessions (§6 pipeline Step 2)
# ---------------------------------------------------------------------------

def build_all_sessions(
    roadmap,
    progress_map: Dict[str, dict],
    *,
    effective_completed_subjects: Set[str],
) -> Dict[str, SubjectLearningSession]:
    """Build learning sessions for every track in the roadmap.

    ``effective_completed_subjects`` is REQUIRED (keyword-only).  It must
    be the union of actual completion and onboarding-derived effective
    completion, as computed by
    ``LearnerContext.effective_completed_subject_ids(roadmap)``.

    This function previously derived ``completed_subjects`` independently
    from node-level progress, ignoring the effective-knowledge signal
    the eligibility engine already respected.  That inconsistency meant
    a learner with PF=9 onboarding would see PF marked "eligible" in
    the session pipeline (no nodes completed → not in completed_subjects)
    even though the eligibility engine already unlocked Java's nodes.
    Making the input explicit and required eliminates this class of bug.
    """
    sessions: Dict[str, SubjectLearningSession] = {}
    for track_id in roadmap.track_ids():
        sessions[track_id] = build_subject_learning_session(
            track_id, roadmap, effective_completed_subjects, progress_map,
        )
    return sessions


# ---------------------------------------------------------------------------
# LearnerGoal (§16) — v1: single implicit default goal
# ---------------------------------------------------------------------------

def _default_goal(roadmap) -> LearnerGoal:
    """The v1 default goal: complete the entire curriculum."""
    return LearnerGoal(
        goal_id="default",
        label="Complete Curriculum",
        required_track_ids=list(roadmap.track_ids()),
        required_depth="core",
    )


# ---------------------------------------------------------------------------
# Subject Selection — Stage 1 (§7)
# ---------------------------------------------------------------------------

def select_subjects_for_today(
    sessions: Dict[str, SubjectLearningSession],
    *,
    recent_track_ids: Optional[List[str]] = None,
    max_subjects: int = 3,
    bundles: Optional[Dict[str, Dict]] = None,
) -> List[Tuple[SubjectLearningSession, str]]:
    """Select which subjects deserve attention today.

    Returns (session, reason_code) tuples.
    Deterministic: same inputs -> same subject selection.

    Priority cascade (§7):
    1. Continue unfinished session (mid-lifecycle)
    2. Serve revision due
    3. Serve assessment due
    4. Continue active subject (continuity)
    5. Start newly eligible subject
    6. Elective enrichment
    """
    selected: List[Tuple[SubjectLearningSession, str]] = []
    used_tracks: Set[str] = set()
    used_bundles: Set[str] = set()
    _bundles = bundles or {}

    def _add(session: SubjectLearningSession, reason: str) -> bool:
        if session.track_id in used_tracks or len(selected) >= max_subjects:
            return False
        selected.append((session, reason))
        used_tracks.add(session.track_id)
        bk = _bundle_for_track(session.track_id, _bundles)
        if bk:
            used_bundles.add(bk)
        return True

    schedulable = {
        tid: s for tid, s in sessions.items()
        if s.status in ("eligible", "active", "paused", "completed")
    }

    # Priority 1: Unfinished sessions (mid-lifecycle topics)
    for tid, s in schedulable.items():
        if s.status == "active" and s.topic_lifecycle in ("practice", "revision", "assessment"):
            _add(s, "continue_session")

    # Priority 2: Revision due
    for tid, s in schedulable.items():
        if s.has_revision_due and s.status in ("active", "completed"):
            _add(s, "revision_due")

    # Priority 3: Assessment due
    for tid, s in schedulable.items():
        if s.has_assessment_due and s.status == "active":
            _add(s, "assessment_ready")

    # Priority 4: Active subjects by continuity (most recently active first)
    active = [
        s for tid, s in schedulable.items()
        if s.status == "active" and tid not in used_tracks
    ]
    active.sort(key=lambda s: s.days_since_activity if s.days_since_activity is not None else 999)

    # First pass: prefer different bundles
    for s in active:
        if len(selected) >= max_subjects:
            break
        bk = _bundle_for_track(s.track_id, _bundles)
        if bk and bk in used_bundles:
            continue
        _add(s, "next_topic" if s.topic_lifecycle == "learning" else "continue_session")

    # Second pass: fill remaining from same-bundle active subjects
    for s in active:
        if len(selected) >= max_subjects:
            break
        _add(s, "next_topic" if s.topic_lifecycle == "learning" else "continue_session")

    # Priority 5: Newly eligible subjects
    if len(selected) < max_subjects:
        eligible = [
            s for tid, s in schedulable.items()
            if s.status == "eligible" and tid not in used_tracks
        ]
        for s in eligible:
            if len(selected) >= max_subjects:
                break
            _add(s, "new_subject")

    return selected[:max_subjects]


# ---------------------------------------------------------------------------
# Mission Explanation Engine (§21)
# ---------------------------------------------------------------------------

def explain_task_selection(
    session: SubjectLearningSession,
    scheduling_reason: str,
) -> str:
    """Generate a human-readable explanation for task selection.

    Pure function.  Deterministic.  No LLM call.
    """
    topic = session.current_topic_label or session.current_node_label or session.track_label
    templates = {
        "continue_session": (
            f"Continuing {topic} \u2014 you're in the {session.topic_lifecycle} stage"
        ),
        "revision_due": (
            f"Revision due for {topic} \u2014 "
            f"last studied {session.days_since_activity or '?'} days ago"
        ),
        "assessment_ready": f"{topic} is ready for assessment",
        "next_topic": f"Starting {topic} in {session.track_label}",
        "new_subject": f"Beginning {session.track_label} \u2014 prerequisites are met",
        "subject_rotation": (
            f"Returning to {session.track_label} \u2014 "
            f"last active {session.days_since_activity or '?'} days ago"
        ),
        "elective": f"{session.track_label} for enrichment",
    }
    return templates.get(scheduling_reason, f"Studying {topic}")


# ---------------------------------------------------------------------------
# Build Daily Learning Plan (§18)
# ---------------------------------------------------------------------------

def build_daily_learning_plan(
    sessions: Dict[str, SubjectLearningSession],
    roadmap,
    *,
    recent_track_ids: Optional[List[str]] = None,
    max_subjects: int = 3,
) -> DailyLearningPlan:
    """Build a coherent daily learning plan from sessions.

    This is the top-level function consumed by the planner.
    Returns a DailyLearningPlan with task plans, narratives, and
    explanations that map to the existing DailyMission fields.
    """
    bundles = derive_subject_bundles(roadmap)
    selected = select_subjects_for_today(
        sessions,
        recent_track_ids=recent_track_ids,
        max_subjects=max_subjects,
        bundles=bundles,
    )

    task_plans: List[TaskPlan] = []
    for session, reason_code in selected:
        if not session.next_node_id:
            continue
        activity, cta = _lifecycle_to_activity(
            session.topic_lifecycle,
            roadmap.get(session.next_node_id) or {},
        )
        explanation = explain_task_selection(session, reason_code)
        lifecycle = session.topic_lifecycle

        # Continuity context
        continuity = ""
        if reason_code == "continue_session":
            continuity = f"Continuing from the {lifecycle} stage"
        elif reason_code == "revision_due":
            continuity = "Review before knowledge fades"
        elif reason_code == "new_subject":
            continuity = f"First topic in {session.track_label}"

        # Lifecycle position
        position = ""
        if session.total_nodes:
            done = session.completed_nodes
            total = session.total_nodes
            position = f"Topic {done + 1} of {total} overall"

        task_plans.append(TaskPlan(
            session=session,
            node_id=session.next_node_id,
            activity_type=activity,
            cta=cta,
            reason_code=reason_code,
            explanation=explanation,
            continuity_context=continuity,
            lifecycle_position=position,
        ))

    # Build narrative
    parts = []
    for tp in task_plans:
        parts.append(tp.explanation)
    narrative = ". ".join(parts) + "." if parts else ""

    # Build insight payload
    task_explanations = [
        {
            "task_index": i,
            "reason_code": tp.reason_code,
            "explanation": tp.explanation,
            "subject": tp.session.track_label,
            "lifecycle": tp.session.topic_lifecycle,
        }
        for i, tp in enumerate(task_plans)
    ]

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return DailyLearningPlan(
        date=today,
        selected_sessions=[s for s, _ in selected],
        task_plans=task_plans,
        plan_narrative=narrative,
        plan_insight={"task_explanations": task_explanations},
    )
