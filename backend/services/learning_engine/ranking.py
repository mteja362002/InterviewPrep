"""Ranking model for additive learning recommendations."""
from __future__ import annotations

from typing import Any, Iterable, List, Optional

from roadmap import get_roadmap
from services.learning_engine.adaptive_weights import (
    DEFAULT_ADAPTIVE_WEIGHTS, ResolvedWeights, resolve_weights,
)
from services.learning_engine.roi import compute_learning_roi

# Legacy per-signal constants kept as module-level aliases so any external
# caller that imported them by name (tests, docs) still sees the same
# numeric values. The canonical source of truth is now
# ``adaptive_weights.DEFAULT_ADAPTIVE_WEIGHTS`` — every weight below
# reads from that dict so tuning happens in ONE place.
_DIFFICULTY_PENALTY = {"easy": 0.0, "medium": 0.2, "hard": 0.4}
_SEQUENCE_GATE_PENALTY = DEFAULT_ADAPTIVE_WEIGHTS["sequence_penalty"]
_RECENCY_PENALTY = DEFAULT_ADAPTIVE_WEIGHTS["recency_penalty"]
_SKIP_DEFERRAL_PENALTY = DEFAULT_ADAPTIVE_WEIGHTS["skip_penalty"]
_TRACK_FATIGUE_PENALTY = DEFAULT_ADAPTIVE_WEIGHTS["fatigue_penalty"]
_FOUNDATION_BONUS = DEFAULT_ADAPTIVE_WEIGHTS["foundation_bonus"]

# Experience bands that grant same-track fatigue penalty. Beginner bands
# ("student", "0-1") are excluded so they can safely stay in the same
# track for consecutive days while learning foundations.
#
# NOTE: this is NOT a hardcoded learner profile — it is a curriculum-
# authored VOCABULARY of experience bands. Extending the vocabulary is
# additive; the scoring formula never inspects a specific band name.
_FATIGUE_ELIGIBLE_POSITIONS = {"1-3", "3-5", "5+"}

_COMPLETED_STATUSES = {"completed", "mastered", "revision_due"}

# Difficulty ordinal used by the smoothness signal (Phase 4 Step 2).
_DIFFICULTY_ORDINAL = {"easy": 0, "medium": 1, "hard": 2}


def _has_incomplete_earlier_sibling(node: dict, progress_map: dict) -> bool:
    """Return True if an earlier-`order` sibling in the same `category` is
    not yet completed — i.e. `node` is a later step in an authored sequence
    that hasn't been earned yet (see `_SEQUENCE_GATE_PENALTY`)."""
    category = node.get("category")
    order = node.get("order")
    if category is None or order is None:
        return False
    roadmap = get_roadmap()
    for sibling in roadmap.get_learning_nodes():
        if sibling.get("category") != category or sibling.get("id") == node.get("id"):
            continue
        sibling_order = sibling.get("order")
        if sibling_order is None or sibling_order >= order:
            continue
        row = progress_map.get(sibling.get("id")) or {}
        status = (row.get("status") or "").lower()
        if status not in _COMPLETED_STATUSES:
            return True
    return False


def _onboarding_score_for_track(onboarding_scores: Optional[dict], track: Optional[str]) -> Optional[float]:
    """Return the learner's self-assessment score (0-10) for a track, or
    None when we have no signal for it. Deliberately conservative —
    a missing entry is treated as "unknown", not as "very low", so we
    don't over-eagerly bias a random beginner toward foundations they
    haven't declared weakness on."""
    if not onboarding_scores or not track:
        return None
    val = onboarding_scores.get(track)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _is_foundation_node(node: dict) -> bool:
    """Return whether a node is a "foundational" entry point for its track.

    Heuristic uses only roadmap-authored fields — no new data. A node
    qualifies when it declares NO prerequisites (i.e. it can be
    entered directly), OR when its category order is 1 (first in
    an authored sequence).
    """
    prereqs = node.get("prerequisites") or []
    if not prereqs:
        return True
    if node.get("order") == 1:
        return True
    return False


# ---------------------------------------------------------------------------
# Phase 4 Step 2 · adaptive-signal helpers
# ---------------------------------------------------------------------------
#
# Each helper below is a pure function of ONE candidate + the learner
# context. They exist so `score_learning_node` reads as a clean weighted
# sum of named terms — you can point at any line and know exactly which
# term it is. Adding a new signal means adding one helper + one weight
# + one line in the summation; no other file needs to change.
#
# All helpers are safe against `context is None` (return 0.0), keeping
# byte-identical output for pre-Phase-4-Step-2 callers.

def _effective_knowledge_gap(node: dict, context: Any) -> float:
    """Blended (self-assessment + actual mastery) knowledge-gap term.

    Uses the LearnerContext.effective_knowledge_score(track), so early
    on the signal comes primarily from the onboarding self-assessment
    and — as the learner completes nodes on the track — it shifts to
    actual mastery. This is the mechanism satisfying Case J
    ("actual progress outweighs onboarding") without any hardcoded
    threshold or if/else.

    When the learner has declared target companies, the gap-signal is
    amplified proportionally to the roadmap-authored company_importance
    of the candidate's track. This is what makes "different companies
    naturally receive different missions" (Cases E, K) fall out of the
    weighted sum instead of a company-specific if/else — a track that
    matters more to the target company sees a bigger gap-signal, so
    weak areas on that track win over weak areas on off-target tracks.
    """
    if context is None:
        return 0.0
    track = node.get("track")
    effective = float(context.effective_knowledge_score(track))
    gap = max(0.0, 100.0 - effective)
    if track and context.target_companies:
        roadmap = get_roadmap()
        max_importance = max(
            (roadmap.company_importance(track, str(c).lower()) for c in context.target_companies),
            default=0,
        )
        # Amplification factor: 0-5 importance → 1x-3x amplification.
        # Kept multiplicative on `gap` so a track the learner already
        # knows well never gets over-amplified — a zero gap stays zero.
        gap *= 1.0 + max_importance / 2.5
    return gap


def _subject_readiness_bonus(node: dict, context: Any) -> float:
    """Small positive bonus proportional to the learning HEADROOM on
    the candidate's track — tracks the learner already knows well get
    proportionally less of it, so this term naturally rotates focus
    toward areas with genuine growth potential.

    Bounded [0, 1]. Multiplied by the resolved
    ``subject_readiness_bonus`` weight at the summation site.
    """
    if context is None:
        return 0.0
    effective = float(context.effective_knowledge_score(node.get("track")))
    return max(0.0, 1.0 - effective / 100.0)


def _subject_transition_bonus(node: dict, context: Any) -> float:
    """Reward candidates on a track that becomes *available* only after
    the learner effectively completes its prerequisite subjects.

    Fires only when: (a) the candidate's track has at least one
    ``subject_prerequisites`` entry, and (b) EVERY prerequisite has
    been effectively completed by the learner. This is what lets the
    scoring model migrate the learner from Programming Fundamentals →
    Java, from Java → DSA/Core CS, from Core CS → LLD/HLD, without any
    scenario-specific branching.
    """
    if context is None:
        return 0.0
    track_id = node.get("track")
    if not track_id:
        return 0.0
    track = get_roadmap().get(track_id)
    prereqs = (track or {}).get("subject_prerequisites") or []
    if not prereqs:
        return 0.0
    effective_done = context.effectively_completed_tracks()
    if not all(pre in effective_done for pre in prereqs):
        return 0.0
    # 1.0 when the candidate's own track is still lightly known (i.e.
    # a genuine "enter this new subject" moment), scaling down as the
    # learner accumulates mastery on it.
    own_score = float(context.effective_knowledge_score(track_id))
    return max(0.0, 1.0 - own_score / 100.0)


def _prerequisite_gap_penalty(node: dict, context: Any) -> float:
    """Penalise candidates in tracks whose subject-prerequisites are
    still weak in effective_knowledge.

    Prevents the ranker from surfacing an "unlocked" HLD node when the
    learner's Java is still 4/10 — advanced content should wait until
    fundamentals firm up.

    Returns the SUM of shortfalls across every prerequisite subject
    (each 0-1). A track with five weak prereqs (like HLD) accumulates
    a much larger penalty than a track with one weak prereq (like
    DSA), which is exactly the discrimination needed to keep
    beginners out of deep, multi-prereq subjects.
    """
    if context is None:
        return 0.0
    track_id = node.get("track")
    if not track_id:
        return 0.0
    track = get_roadmap().get(track_id)
    prereqs = (track or {}).get("subject_prerequisites") or []
    if not prereqs:
        return 0.0
    total_shortfall = 0.0
    for pre in prereqs:
        eff = float(context.effective_knowledge_score(pre))
        total_shortfall += max(0.0, 100.0 - eff) / 100.0
    return total_shortfall


def _momentum_bonus(node: dict, context: Any) -> float:
    """Small bonus for candidates on tracks where the learner is
    actively completing nodes right now — rewards a healthy streak.
    Uses ``recent_track_ids``. Bounded [0, 1]."""
    if context is None:
        return 0.0
    track = node.get("track")
    if not track:
        return 0.0
    recent = list(context.recent_track_ids or [])
    if not recent:
        return 0.0
    hits = sum(1 for t in recent[-5:] if t == track)
    return min(1.0, hits / 3.0)  # 3+ recent hits = full bonus


def _topic_freshness_penalty(node: dict, context: Any) -> float:
    """Penalise candidates whose TOPIC (not just node id) was completed
    very recently. Prevents same-topic repetition even across
    different leaf nodes. Bounded [0, 1]."""
    if context is None:
        return 0.0
    topic = node.get("topic") or node.get("subtopic")
    if not topic:
        return 0.0
    recent_topics = context.recent_topics(limit=5)
    if not recent_topics:
        return 0.0
    if topic in recent_topics[-3:]:
        return 1.0
    if topic in recent_topics:
        return 0.5
    return 0.0


def _difficulty_smoothness_penalty(node: dict, context: Any) -> float:
    """Penalise a hard jump from the learner's current effective mastery
    to the candidate's authored difficulty.

    Effective mastery is bucketed into three bands (easy: <40, medium:
    40-70, hard: ≥70); the penalty grows as the candidate's difficulty
    steps beyond that band. This is what enforces "no jumping to
    advanced" without a hardcoded difficulty ladder — the ladder is
    derived from live mastery.
    """
    if context is None:
        return 0.0
    difficulty = (node.get("difficulty") or "medium").lower()
    node_level = _DIFFICULTY_ORDINAL.get(difficulty, 1)
    mastery = float(context.effective_knowledge_score(node.get("track")))
    if mastery >= 70.0:
        learner_level = 2  # hard
    elif mastery >= 40.0:
        learner_level = 1  # medium
    else:
        learner_level = 0  # easy
    gap = node_level - learner_level
    if gap <= 0:
        return 0.0
    return min(1.0, gap / 2.0)


def _revision_confidence_bonus(node: dict, progress: dict, context: Any) -> float:
    """Small extra weight when the candidate is BOTH revision-due AND the
    learner's confidence has dropped since completion — precisely the
    case where spaced-repetition needs to fire strongly.
    """
    if context is None:
        return 0.0
    if not progress:
        return 0.0
    next_revision = progress.get("next_revision")
    if not next_revision:
        return 0.0
    try:
        confidence = float(progress.get("confidence", 0.0) or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    # Confidence < 6/10 on a revision-due node = strong forget signal.
    if confidence >= 6.0:
        return 0.0
    return min(1.0, (6.0 - confidence) / 6.0)


def score_learning_node(
    node: dict,
    progress: Optional[dict] = None,
    *,
    target_companies: Optional[Iterable[str]] = None,
    urgency: float = 0.0,
    progress_map: Optional[dict] = None,
    recent_node_ids: Optional[Iterable[str]] = None,
    skipped_node_ids: Optional[Iterable[str]] = None,
    recent_track_ids: Optional[Iterable[str]] = None,
    position: Optional[str] = None,
    onboarding_scores: Optional[dict] = None,
    learner_context: Optional[Any] = None,
    weights: Optional[ResolvedWeights] = None,
) -> dict:
    """Score one candidate node and return every factor that produced the score.

    This is the single scoring implementation `rank_learning_nodes` uses to sort
    candidates. `services/learning_engine/insight.py` calls it again for just the
    winning node so the "why was this picked" explanation can never drift from
    what actually ranked it — there is no second, duplicated scoring formula.

    All keyword arguments are OPTIONAL. Callers who omit
    ``learner_context`` get byte-identical scores to before Phase 4
    Step 2 (adaptive terms all evaluate to zero without a context).

    ``learner_context`` (Phase 4 Step 2) is a
    :class:`services.learning_engine.context.LearnerContext`. Passing
    it activates the adaptive signal terms:
        - effective_knowledge_gap (blended self-assessment + actual)
        - subject_readiness_bonus (learning-headroom bonus)
        - subject_transition_bonus (rewards a track becoming available)
        - prerequisite_gap_penalty (guard against advanced-content jumps)
        - momentum_bonus (rewards active streaks on the same track)
        - topic_freshness_penalty (variety across days)
        - difficulty_smoothness_penalty (no big difficulty jumps)
        - revision_confidence_bonus (spaced-repetition + forget signal)

    ``weights`` allows a caller to override a subset of weights for
    experimentation without recomputing the full pipeline. Defaults to
    the canonical :data:`adaptive_weights.DEFAULT_ADAPTIVE_WEIGHTS`.
    """
    progress = progress or {}
    companies = [company.lower() for company in (target_companies or [])]
    w = weights if isinstance(weights, ResolvedWeights) else resolve_weights()

    confidence = float(progress.get("confidence", 0.0) or 0.0)
    weakness = float(progress.get("weakness_score", 100.0) or 100.0)
    mastery = float(
        progress.get("mastery_percentage", progress.get("mastery", 0.0)) or 0.0
    )
    difficulty = (node.get("difficulty") or "medium").lower()
    estimated_minutes = int(node.get("estimated_minutes") or 0)
    mastery_weight = float(node.get("mastery_weight") or 1.0)
    node_id = node.get("id")
    track = node.get("track")

    # roadmap_v1.json currently authors a uniform company_importance value on
    # every individual leaf node (no per-node variance), while its real,
    # differentiated company signal lives one level up on each track. Look up
    # by track so DSA-heavy companies (e.g. Google) and Java/DBMS-heavy
    # companies (e.g. Oracle) actually diverge across a multi-track candidate
    # pool. Falls back to the node id if it has no track.
    roadmap = get_roadmap()
    company_key = track or node_id
    company_score = sum(roadmap.company_importance(company_key, company) for company in companies)

    # ---- Phase 2B · Company Intelligence term ---------------------------
    # Bounded ADDITIVE nudge from compiled Company Intelligence. Active ONLY
    # when the LearnerContext opted in AND carries a non-empty company_context.
    # Any failure degrades to 0.0 so the planner falls back to the roadmap-only
    # company_score (deterministic, never raises).
    company_intel_score = 0.0
    company_intel_breakdown = None
    if learner_context is not None and getattr(learner_context, "company_intelligence_enabled", False):
        cc = getattr(learner_context, "company_context", None)
        if cc is not None and not getattr(cc, "is_empty", True):
            try:
                from company_intelligence.scoring import (
                    compute_company_intelligence_signal,
                    experience_level_from_position,
                )
                level = experience_level_from_position(getattr(learner_context, "position", None))
                company_intel_score, contributions = compute_company_intelligence_signal(
                    cc, node, level=level,
                )
                if contributions:
                    from company_intelligence.explainability import summarize_contributions
                    company_intel_breakdown = summarize_contributions(contributions)
            except Exception:  # pragma: no cover - defensive fallback
                company_intel_score = 0.0
                company_intel_breakdown = None

    # ---- Phase 2C · Learner Intelligence term ---------------------------
    # Bounded ADDITIVE nudge from the precomputed LearnerIntelligenceSnapshot.
    # Active ONLY when the LearnerContext opted in AND carries a non-empty
    # snapshot. Any failure degrades to 0.0 so the planner falls back to its
    # pre-2C scoring (deterministic, never raises). The snapshot is computed
    # ONCE per context (compute-once / consume-many) — this reads it, it does
    # not recompute learner history per candidate.
    learner_intel_score = 0.0
    learner_intel_breakdown = None
    if learner_context is not None and getattr(learner_context, "learner_intelligence_enabled", False):
        li = getattr(learner_context, "learner_intelligence", None)
        if li is not None and not getattr(li, "is_empty", True):
            try:
                from services.learner_intelligence.planner_adapter import (
                    learner_intelligence_signal,
                )
                learner_intel_score, li_contributions = learner_intelligence_signal(
                    li, node, position=position,
                )
                if li_contributions:
                    from services.learner_intelligence.explainability import (
                        summarize_contributions as _summarize_li,
                    )
                    learner_intel_breakdown = _summarize_li(li_contributions)
            except Exception:  # pragma: no cover - defensive fallback
                learner_intel_score = 0.0
                learner_intel_breakdown = None

    difficulty_penalty = _DIFFICULTY_PENALTY.get(difficulty, 0.2)
    interview_importance = float(node.get("interview_importance") or 0.0)
    interview_frequency = float(node.get("interview_frequency") or 0.0)
    urgency_bonus = urgency * (
        interview_importance * 3.0
        + interview_frequency * 3.0
        - min(estimated_minutes, 90) * 0.03
    )
    knowledge_gap = (
        (100.0 - confidence * 10.0) * 0.45
        + weakness * 0.35
        + (100.0 - mastery) * 0.15
    )

    roi = compute_learning_roi(node_id)
    roi_score = roi["roi_score"]

    sequence_penalty = (
        w["sequence_penalty"]
        if progress_map is not None and _has_incomplete_earlier_sibling(node, progress_map)
        else 0.0
    )
    recency_penalty = (
        w["recency_penalty"] if node_id and node_id in (recent_node_ids or ()) else 0.0
    )

    # ---- RC1.3.3 · skipped-node deferral --------------------------------
    skip_penalty = (
        w["skip_penalty"]
        if node_id and node_id in (skipped_node_ids or ())
        else 0.0
    )

    # ---- RC1.3.3 · same-track fatigue -----------------------------------
    # Applies only when the learner is mid+ experience AND the last two
    # missions were on this same track. Beginners are excluded.
    fatigue_penalty = 0.0
    recent_tracks_list = list(recent_track_ids or ())
    if (
        track
        and position in _FATIGUE_ELIGIBLE_POSITIONS
        and len(recent_tracks_list) >= 2
        and recent_tracks_list[-1] == track
        and recent_tracks_list[-2] == track
    ):
        fatigue_penalty = w["fatigue_penalty"]

    # ---- RC1.3.3 · foundation-first bias --------------------------------
    # Kick in only when the learner has a *declared* low self-assessment
    # on this track AND the candidate is a foundational entry point AND
    # (Phase 4 Step 2) — when a LearnerContext is supplied — the track's
    # subject-prerequisites are effectively complete. Firing the bonus on
    # a foundational node in a track the learner isn't ready to enter yet
    # (e.g. HLD when Java is still unknown) was letting the model surface
    # "unlocked but way-too-advanced" nodes; gating on effective subject-
    # DAG readiness removes that failure mode.
    onboarding_track_score = _onboarding_score_for_track(onboarding_scores, track)
    foundation_bonus = 0.0
    if onboarding_track_score is not None and onboarding_track_score < 3.5 and _is_foundation_node(node):
        subject_ready = True
        if learner_context is not None and track:
            track_meta = roadmap.get(track)
            subject_prereqs = (track_meta or {}).get("subject_prerequisites") or []
            if subject_prereqs:
                effectively_done = learner_context.effectively_completed_tracks()
                subject_ready = all(pre in effectively_done for pre in subject_prereqs)
        if subject_ready:
            foundation_bonus = w["foundation_bonus"]

    # ---- Phase 4 Step 2 · adaptive signal terms -------------------------
    # Each term is a scalar in a bounded range multiplied by its
    # centralised weight. All terms evaluate to 0.0 when
    # ``learner_context is None`` so the pre-Phase-4-Step-2 output is
    # preserved byte-for-byte.
    effective_gap = _effective_knowledge_gap(node, learner_context)
    subject_readiness = _subject_readiness_bonus(node, learner_context)
    subject_transition = _subject_transition_bonus(node, learner_context)
    prereq_gap = _prerequisite_gap_penalty(node, learner_context)
    momentum = _momentum_bonus(node, learner_context)
    topic_freshness = _topic_freshness_penalty(node, learner_context)
    difficulty_smoothness = _difficulty_smoothness_penalty(node, learner_context)
    revision_confidence = _revision_confidence_bonus(node, progress, learner_context)

    total_score = (
        knowledge_gap * mastery_weight
        + effective_gap * w["effective_knowledge_gap"]
        + company_score * w["company_score"]
        + company_intel_score * w["company_intelligence_score"]
        + learner_intel_score * w["learner_intelligence_score"]
        + roi_score * w["roi_score"]
        - difficulty_penalty * w["difficulty_penalty"]
        - min(estimated_minutes, 60) * w["estimated_minutes"]
        + urgency_bonus
        - sequence_penalty
        - recency_penalty
        - skip_penalty
        - fatigue_penalty
        + foundation_bonus
        + subject_readiness * w["subject_readiness_bonus"]
        + subject_transition * w["subject_transition_bonus"]
        - prereq_gap * w["prerequisite_gap_penalty"]
        + momentum * w["momentum_bonus"]
        - topic_freshness * w["topic_freshness_penalty"]
        - difficulty_smoothness * w["difficulty_smoothness_penalty"]
        + revision_confidence * w["revision_confidence_bonus"]
    )

    return {
        "node_id": node_id,
        "total_score": total_score,
        "knowledge_gap": knowledge_gap,
        "confidence": confidence,
        "weakness": weakness,
        "mastery": mastery,
        "mastery_weight": mastery_weight,
        "company_score": company_score,
        "company_intelligence_score": company_intel_score,
        "company_intelligence": company_intel_breakdown,
        "learner_intelligence_score": learner_intel_score,
        "learner_intelligence": learner_intel_breakdown,
        "difficulty": difficulty,
        "difficulty_penalty": difficulty_penalty,
        "estimated_minutes": estimated_minutes,
        "interview_importance": interview_importance,
        "interview_frequency": interview_frequency,
        "urgency": urgency,
        "urgency_bonus": urgency_bonus,
        "roi": roi,
        "sequence_penalty": sequence_penalty,
        "recency_penalty": recency_penalty,
        # RC1.3.3 · additive audit fields — surfaced in the "why this?"
        # dialog through the same insight pipeline so learners can see
        # exactly which nudge fired.
        "skip_penalty": skip_penalty,
        "fatigue_penalty": fatigue_penalty,
        "foundation_bonus": foundation_bonus,
        # Phase 4 Step 2 · adaptive audit fields.
        "effective_knowledge_gap": effective_gap,
        "subject_readiness_bonus": subject_readiness,
        "subject_transition_bonus": subject_transition,
        "prerequisite_gap_penalty": prereq_gap,
        "momentum_bonus": momentum,
        "topic_freshness_penalty": topic_freshness,
        "difficulty_smoothness_penalty": difficulty_smoothness,
        "revision_confidence_bonus": revision_confidence,
    }


def rank_learning_nodes(
    candidates: Iterable[dict],
    progress_map: Optional[dict] = None,
    *,
    target_companies: Optional[Iterable[str]] = None,
    urgency: float = 0.0,
    recent_node_ids: Optional[Iterable[str]] = None,
    skipped_node_ids: Optional[Iterable[str]] = None,
    recent_track_ids: Optional[Iterable[str]] = None,
    position: Optional[str] = None,
    onboarding_scores: Optional[dict] = None,
    learner_context: Optional[Any] = None,
    weights: Optional[ResolvedWeights] = None,
) -> List[dict]:
    """Rank nodes by a simple, isolated scoring model (see `score_learning_node`).

    When two candidates land on the same overall score, the one more relevant
    to the learner's target companies is preferred (`company_score` tie-break).

    All RC1.3.3 additions are forwarded to `score_learning_node`. Each is
    optional (default None) — callers that don't pass them get byte-
    identical ranking to before.

    Phase 4 Step 2 additions (``learner_context``, ``weights``) are also
    fully optional — passing them activates the adaptive signal terms
    described in ``score_learning_node``.
    """
    progress_map = progress_map or {}

    scored = []
    for node in candidates:
        breakdown = score_learning_node(
            node,
            progress_map.get(node.get("id"), {}),
            target_companies=target_companies,
            urgency=urgency,
            progress_map=progress_map,
            recent_node_ids=recent_node_ids,
            skipped_node_ids=skipped_node_ids,
            recent_track_ids=recent_track_ids,
            position=position,
            onboarding_scores=onboarding_scores,
            learner_context=learner_context,
            weights=weights,
        )
        scored.append((breakdown["total_score"], breakdown["company_score"], node))

    return [
        node
        for _, _, node in sorted(scored, key=lambda item: (item[0], item[1]), reverse=True)
    ]
