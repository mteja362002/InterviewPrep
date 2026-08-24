"""Eligibility Engine (RC1.3.6A · Phase 4).

Sits between the Learning State (Phase 3) and Candidate Generation (Phase 5)
in the intended pipeline:

    Roadmap -> Prerequisite Graph -> Learning State -> Eligibility Engine
    -> Candidate Set -> Ranking Engine -> Mission Planner

Produces the set of roadmap learning nodes that are genuinely eligible for
recommendation *today*, so the ranking engine (services/learning_engine/
ranking.py, left untouched — Phase 6 only changes what it is called with)
never has to inspect an ineligible node. Every gate here REUSES an existing,
already-fixed signal instead of re-deriving it:

  - Prerequisite graph: `unlock.get_unlocked_nodes()` (Phase-1-fixed
    container-prerequisite propagation).
  - Learning stage / onboarding progression: `stage_engine`'s
    `SubjectLearningState.next_eligible_stage` (Phase 3), which is itself
    already the product of Phase 2's stage-aware onboarding seed.
  - Completed nodes: the same completed-status set unlock.py already uses.
  - Revision rules: revision-due nodes are handled entirely by the existing
    `revision.get_highest_priority_revision` short-circuit in planner.py,
    which runs *before* this layer and wins unconditionally — this layer
    only has to avoid re-excluding a `status="revision_due"` node that the
    revision path did not pick (it is naturally excluded as "completed",
    which is correct: it is not a *new* candidate, it is a scheduled repeat).
  - Interview urgency / company compatibility: interview urgency widens the
    stage cap to admit interview-stage (case-study) content (see
    `_stage_cap_index`); company compatibility is intentionally NOT a hard
    gate here (no roadmap node is fundamentally "incompatible" with a
    company) — it is a weighting signal, already owned by
    `ranking.score_learning_node`'s company term and by Candidate
    Generation's company-priority trimming (Phase 5). Duplicating it as a
    second hard filter here would risk zeroing out an entire off-target
    track's candidates.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from services.learning_engine.stage_engine import SubjectLearningState, _STAGE_ORDER
from services.learning_engine.unlock import get_unlocked_nodes
from services.progress_engine import _node_stage_index

# Matches the pacing engine's ACCELERATED/CRITICAL urgency tiers
# (services/learning_engine/pacing.py) — "interview urgency" widening only
# kicks in once the learner is genuinely time-pressured.
INTERVIEW_URGENCY_THRESHOLD = 0.7

_COMPLETED_STATUSES = {"completed", "mastered", "revision_due"}


def _stage_cap_index(subject_state: SubjectLearningState, *, urgency: float = 0.0) -> int:
    """Highest node-stage index eligible for this subject right now.

    Normally capped at `next_eligible_stage` (never skips more than one
    stage past the learner's current progress in this subject — this is the
    concrete mechanism that stops a beginner from reaching "advanced" DP/HLD/
    LLD content even when that content has no authored prerequisites of its
    own). Widened to admit the "interview"/capstone stage once the learner
    has reached "advanced" in this subject, or once interview urgency is
    high — otherwise case-study/company-focused content could never win a
    plain stage-progression comparison.
    """
    cap = _STAGE_ORDER.index(subject_state.next_eligible_stage)
    if subject_state.current_stage == "advanced" or urgency >= INTERVIEW_URGENCY_THRESHOLD:
        return len(_STAGE_ORDER)  # admits "interview" / "company_specific" stage nodes too
    return cap


def eligible_learning_nodes(
    progress_rows: Dict[str, dict],
    subject_states: Dict[str, SubjectLearningState],
    *,
    urgency: float = 0.0,
    skip_node_ids: Optional[Iterable[str]] = None,
    virtual_completed_node_ids: Optional[Iterable[str]] = None,
) -> List[dict]:
    """Return roadmap learning nodes that are genuinely eligible today.

    `progress_rows` is the standard node_id -> knowledge_nodes-row dict
    (`progress_engine.load_user_progress_rows`); `subject_states` is the
    output of `stage_engine.compute_all_subject_states` for the same user.

    ``virtual_completed_node_ids`` (Phase 4 Step 2, optional) is a set of
    leaf-node ids the planner treats as *effectively* completed for
    subject-DAG unlocking. This is populated by
    :meth:`LearnerContext.virtual_completed_node_ids` from tracks whose
    blended (self-assessment + actual) effective knowledge exceeds
    :data:`context.EFFECTIVE_SUBJECT_COMPLETE_THRESHOLD`, and it is
    used ONLY inside the planner pipeline — KB/UI unlock rules keep
    consuming the real, actual completion set. Absent (default None)
    keeps the pre-Phase-4-Step-2 behaviour byte-identical.
    """
    # Local import to avoid a cycle at module import time.
    from services.learning_engine.unlock import get_curriculum_eligible_nodes as _base_get_unlocked

    skip_ids = set(skip_node_ids or [])
    completed_ids = {
        nid for nid, row in progress_rows.items()
        if (row.get("status") or "").lower() in _COMPLETED_STATUSES
    }
    virtual = set(virtual_completed_node_ids or [])

    if virtual:
        # Union actual completions with virtual ones for the unlock walk.
        # Emit synthetic "completed" rows so the roadmap unlock helper
        # (which reads status) treats them as done.
        merged_rows = list(progress_rows.values())
        merged_rows.extend(
            {"node_id": nid, "status": "completed"} for nid in virtual if nid not in completed_ids
        )
        unlocked = _base_get_unlocked(merged_rows)
    else:
        unlocked = _base_get_unlocked(list(progress_rows.values()))

    eligible: List[dict] = []
    for node in unlocked:
        node_id = node.get("id")
        # Skip both fully-completed and virtually-completed nodes — a
        # virtually-completed track's nodes are treated as done, not as
        # today's next step.
        if node_id in completed_ids or node_id in skip_ids or node_id in virtual:
            continue
        subject_state = subject_states.get(node.get("track"))
        if subject_state is None:
            # No stage state computed for this track (should not normally
            # happen — compute_all_subject_states covers every roadmap
            # track) — fail open rather than silently dropping real nodes.
            eligible.append(node)
            continue
        cap = _stage_cap_index(subject_state, urgency=urgency)
        if _node_stage_index(node) <= cap:
            eligible.append(node)
    return eligible
