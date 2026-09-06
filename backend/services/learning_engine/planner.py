"""Adaptive Learning Planner — Phase 4 orchestrator.

Purpose:
    The planner is now a THIN ORCHESTRATOR. It sequences four
    single-responsibility engines and stitches their outputs into a
    recommendation dict. It does NOT contain scoring rules, learner
    profile branching, or company-specific if/else chains — those live
    in dedicated modules that are individually testable and
    individually extensible.

Pipeline (Phase 4 Step 1):

    LearnerContext  <-- one bundle of learner-scoped signals
        |
        v
    revision short-circuit  <-- if a spaced-repetition item is due,
        |                       it wins; the engine below is not run.
        v
    Eligibility Engine  <-- what is legally allowed today
        |                   (unlock + stage cap + skip hints)
        v
    Cold-Start Strategy  <-- for first-time learners, the roadmap's
        |                    own entry track wins; no scoring override.
        v
    Candidate Generation  <-- narrow to a compact ~15-30 node set
        |
        v
    Priority Engine  <-- generalized scoring + continuity tie-break
        |
        v
    Companion (support + core) <-- metadata-driven fallback ladders
        |
        v
    Insight Builder + Foresight <-- explainable "why this?" payload
        |
        v
    build_learning_recommendation --> DTO returned to the caller

Compatibility:
    The public signature of `get_today_learning_node` is unchanged.
    Every keyword argument has the same meaning and default it had
    before Phase 4. All existing callers (`routes_missions`,
    `mission_engine`, the test suite) keep working with no changes.
"""
from __future__ import annotations

from typing import Iterable, Optional

from services.learning_engine.builder import build_learning_recommendation
from services.learning_engine.candidates import generate_candidate_nodes
from services.learning_engine.cold_start import cold_start_candidate
from services.learning_engine.companion import (
    core_recommendation, support_recommendation,
)
from services.learning_engine.context import LearnerContext, build_learner_context
from services.learning_engine.eligibility import eligible_learning_nodes
from services.learning_engine.foresight import (
    estimate_company_readiness_gain, likely_next_topics,
)
from services.learning_engine.insight import build_recommendation_insight
from services.learning_engine.pacing import forecast_completion
from services.learning_engine.priority_engine import (
    PriorityScore, score_candidate, top_candidate,
)
from services.learning_engine.revision import get_highest_priority_revision
from services.learning_engine.stage_engine import compute_all_subject_states
from services.progress_engine import load_user_progress_rows
from roadmap import get_roadmap


# ---------------------------------------------------------------------------
# Internal helpers — assembly, not decision-making
# ---------------------------------------------------------------------------

async def _load_progress_rows(user_id: str, db=None) -> list:
    """Load canonical roadmap progress rows from `knowledge_nodes`.

    This is the same collection every other consumer of learner state
    reads (mission engine, KB, feedback workflow). Reading from a
    different source made the planner observe learner state that
    disagreed with everything else the app displayed — a defect fixed
    before Phase 4 and preserved here.
    """
    if db is None:
        return []
    rows = await load_user_progress_rows(db, user_id)
    return list(rows.values())


def _attach_insight(
    priority: PriorityScore,
    context: LearnerContext,
) -> dict:
    """Assemble the explainable insight payload for one winning node.

    Pure over already-computed signals — the priority breakdown, the
    roadmap-graph foresight helpers, and the pacing forecast — so the
    "why this?" explanation can never contradict what the priority
    engine actually chose.
    """
    node = priority.node
    forecast = forecast_completion(context.pacing_state, completed_dates=context.completed_dates)
    likely = likely_next_topics(node.get("id"), completed_ids=context.completed_node_ids())

    readiness_est = None
    if context.onboarding and context.knowledge_rows:
        readiness_est = estimate_company_readiness_gain(
            node,
            onboarding=context.onboarding,
            knowledge_rows=context.knowledge_rows,
            target_companies=context.target_companies or [],
            difficulty=(node.get("difficulty") or "medium"),
        )

    # Phase 2C: the learner-level explainability block (difficulty action,
    # confidence band, readiness trajectory, reasons) is derived from the
    # precomputed snapshot only when Learner Intelligence is enabled and
    # non-empty. Absent otherwise -> pre-2C insight payload, byte-identical.
    learner_intel_summary = None
    li_snapshot = getattr(context, "learner_intelligence", None)
    if (
        getattr(context, "learner_intelligence_enabled", False)
        and li_snapshot is not None
        and not getattr(li_snapshot, "is_empty", True)
    ):
        try:
            from services.learner_intelligence.explainability import summarize_snapshot
            learner_intel_summary = summarize_snapshot(li_snapshot, node=node)
        except Exception:  # pragma: no cover - defensive
            learner_intel_summary = None

    return build_recommendation_insight(
        node,
        score_breakdown=priority.breakdown,
        target_companies=context.target_companies,
        pacing_state=context.pacing_state,
        forecast=forecast,
        continuity=priority.continuity,
        likely_next_topics=likely,
        readiness_delta_estimate=readiness_est,
        learner_intelligence=learner_intel_summary,
    )


def _finalize(
    node: dict,
    progress: dict,
    context: LearnerContext,
    *,
    insight: dict,
) -> dict:
    """Bundle the winning node with its companion recommendations and
    the pre-built insight into the canonical recommendation DTO."""
    return build_learning_recommendation(
        node,
        progress=progress,
        support_recommendation=support_recommendation(node, context),
        core_recommendation=core_recommendation(context),
        insight=insight,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def get_today_learning_node(
    user_id: str, *,
    db=None,
    pacing_state: Optional[dict] = None,
    target_companies: Optional[Iterable[str]] = None,
    completed_dates: Optional[Iterable[str]] = None,
    recent_node_ids: Optional[Iterable[str]] = None,
    onboarding: Optional[dict] = None,
    knowledge_rows: Optional[list] = None,
    recent_completions: Optional[Iterable[dict]] = None,
    skip_node_ids: Optional[Iterable[str]] = None,
    skipped_node_ids: Optional[Iterable[str]] = None,
    recent_track_ids: Optional[Iterable[str]] = None,
    company_intelligence: bool = False,
    learner_intelligence: bool = False,
) -> Optional[dict]:
    """Return the best learning recommendation for the user.

    Signature is byte-identical to the pre-Phase-4 planner. All
    keyword arguments remain optional; callers that pass only
    ``user_id + db`` get identical output to before.

    * ``pacing_state`` (services/learning_engine/pacing.py) — urgency /
      capacity signal. Defaults to no-op.
    * ``target_companies`` — list of target company ids for
      company-weighted scoring.
    * ``completed_dates`` — full completion-date history used only for
      the forecast attached to the insight; never affects picks.
    * ``recent_node_ids`` — node ids offered in recent missions; feeds
      the recency penalty in ranking.
    * ``onboarding`` + ``knowledge_rows`` — enable per-company
      readiness estimate and the foundation-first bias.
    * ``recent_completions`` — enables continuity tie-break.
    * ``skip_node_ids`` — RETRY hint from ``validate_mission`` after
      the validator flags a first attempt; those nodes are excluded
      from eligibility.
    * ``skipped_node_ids`` — nodes the learner SKIPPED in recent
      missions (deferral penalty in ranking).
    * ``recent_track_ids`` — recent-mission track order (fatigue
      penalty for mid+ learners).
    """
    progress_rows = await _load_progress_rows(user_id, db)

    context = build_learner_context(
        onboarding=onboarding,
        progress_rows=progress_rows,
        pacing_state=pacing_state,
        target_companies=target_companies,
        recent_completions=recent_completions,
        recent_node_ids=recent_node_ids,
        recent_track_ids=recent_track_ids,
        skipped_node_ids=skipped_node_ids,
        completed_dates=completed_dates,
        knowledge_rows=knowledge_rows,
        skip_node_ids=skip_node_ids,
        company_intelligence_enabled=company_intelligence,
        learner_intelligence_enabled=learner_intelligence,
    )

    # ---- 1. Revision short-circuit ---------------------------------------
    # Spaced-repetition items ALWAYS win over new content. This gate is a
    # single-line pipeline stage — never a branching decision the planner
    # itself owns beyond "did the engine surface one?".
    revision = get_highest_priority_revision(user_id, progress_rows=progress_rows)
    if revision is not None and revision.get("node_id") not in context.skip_node_ids:
        roadmap = get_roadmap()
        node = roadmap.get(revision.get("node_id"))
        if node is not None:
            priority = score_candidate(node, context)
            # For a revision pick, priority is informational (we didn't
            # rank against anything else) — but the same insight
            # pipeline runs so the explanation object is consistent.
            insight = _attach_insight(priority, context)
            return _finalize(node, revision, context, insight=insight)

    # ---- 2. Eligibility engine ------------------------------------------
    # Phase 4 Step 2: virtual completions from tracks with high effective
    # knowledge propagate into the subject-DAG unlock so a learner who
    # self-declares strong Programming Fundamentals can immediately
    # progress into Java on day one (Case A3), etc. These "virtual"
    # completions are never persisted; only the planner sees them.
    virtual_completed = context.virtual_completed_node_ids()
    roadmap = get_roadmap()
    subject_states = compute_all_subject_states(roadmap, context.progress_map)
    eligible = eligible_learning_nodes(
        context.progress_map, subject_states,
        urgency=context.urgency, skip_node_ids=context.skip_node_ids,
        virtual_completed_node_ids=virtual_completed,
    )
    if not eligible:
        return None

    # ---- 3. Cold-start strategy -----------------------------------------
    # First-session learners land on the roadmap-declared entry track.
    # This is a signal-driven strategy; it fires when the DATA matches
    # — never based on a hardcoded learner profile.
    entry_node = cold_start_candidate(eligible, context)
    if entry_node is not None:
        priority = score_candidate(entry_node, context)
        insight = _attach_insight(priority, context)
        entry_progress = context.progress_map.get(entry_node.get("id") or "", {})
        return _finalize(entry_node, entry_progress, context, insight=insight)

    # ---- 3.5 Curriculum Progression Engine (session-based pipeline) ------
    # The session pipeline builds a SubjectLearningSession for every
    # track, selects the best subjects for today, and picks the
    # deterministic next topic within each.  If it produces a primary
    # recommendation, it wins.  If not (e.g. all subjects mastered),
    # the fallback candidate pipeline below runs.
    try:
        from services.learning_engine.subject_progression import (
            build_all_sessions, build_daily_learning_plan,
        )
        sessions = build_all_sessions(
            roadmap,
            context.progress_map,
            effective_completed_subjects=context.effective_completed_subject_ids(roadmap),
        )
        plan = build_daily_learning_plan(
            sessions, roadmap,
            recent_track_ids=list(context.recent_track_ids or []),
        )
        if plan.task_plans:
            primary = plan.task_plans[0]
            node = roadmap.get(primary.node_id)
            if node is not None:
                priority = score_candidate(node, context)
                insight = _attach_insight(priority, context)
                # Enrich insight with session explanations
                insight["task_explanations"] = plan.plan_insight.get("task_explanations", [])
                if plan.plan_narrative:
                    insight["plan_narrative"] = plan.plan_narrative
                top_progress = context.progress_map.get(primary.node_id, {})
                return _finalize(node, top_progress, context, insight=insight)
    except Exception:
        # Defensive: if the session pipeline fails for any reason,
        # fall through to the existing candidate generation pipeline.
        # This guarantees backward compatibility during rollout.
        pass

    # ---- 4. Candidate generation (FALLBACK) -----------------------------
    candidates = generate_candidate_nodes(
        eligible, context.progress_map, subject_states, roadmap=roadmap,
        target_companies=context.target_companies, urgency=context.urgency,
        recent_track_ids=context.recent_track_ids,
    )
    if not candidates:
        return None

    # ---- 5. Priority engine + continuity tie-break ----------------------
    top = top_candidate(candidates, context)
    if top is None:
        return None

    # ---- 6. Assemble the recommendation ---------------------------------
    top_progress = context.progress_map.get(top.node.get("id") or "", {})
    insight = _attach_insight(top, context)
    return _finalize(top.node, top_progress, context, insight=insight)

