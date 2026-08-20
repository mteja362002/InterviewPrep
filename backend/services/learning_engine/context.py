"""LearnerContext — the single bundle of learner-scoped signals the
adaptive planning pipeline consumes.

Purpose (Phase 4 Step 1):
    The planner previously threaded ~10 individual keyword arguments
    through every scoring / candidate / insight call. Every time a new
    adaptive signal was introduced (skipped nodes, track fatigue,
    foundation bias, continuity …), every intermediate function had
    to grow another parameter. That coupling is what the Phase 4 brief
    explicitly asks us to remove: "New … learner attributes, and
    scoring signals should be introducible without requiring planner
    redesign or large conditional changes."

    Bundling them in ONE dataclass turns extension into an additive
    change: add a new field here, teach whichever engine layer cares
    about it to read it, and the planner code path stays untouched.

Design contract:
    * PURE data. Never touches Mongo, never fetches roadmap nodes
      directly, never mutates. The planner is responsible for
      populating it; every layer downstream is read-only.
    * OPTIONAL everywhere. Every field defaults to a safe empty value
      so a caller that only passes user_id + db still gets identical
      behaviour to the pre-refactor planner.
    * DETERMINISTIC. Derived properties (completed_node_ids,
      continuity_chain) are computed the same way as the pre-Phase-4
      code so the recommendation output is byte-identical for the same
      inputs.
    * METADATA-DRIVEN. No hardcoded position enums, no company-specific
      branching, no scenario-specific if/else lives here. Higher-level
      strategies (cold_start.py, companion.py, priority_engine.py) read
      these signals but never encode learner identities.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Set

from services.learning_engine.composition import (
    ContinuityChain, chain_from_history,
)

if TYPE_CHECKING:  # avoid any runtime import cost / cycle
    from services.learning_engine.company_context import CompanyContext

_COMPLETED_STATUSES = {"completed", "mastered", "revision_due"}

# Phase 4 Step 2 · Effective-knowledge blending.
#
# The planner should trust ACTUAL mastery over the learner's onboarding
# self-assessment as evidence accumulates. We model this as a sigmoid-
# style ramp where the blend weight α on actual mastery grows with the
# number of completed nodes in the track. With 0 completions α ≈ 0 (all
# signal comes from self-assessment); with `EVIDENCE_HALF_LIFE`
# completions α = 0.5 (equal weight); asymptotically α → 1 (self-
# assessment is ignored).
#
# The half-life is deliberately low (2 completions) so a learner who has
# actually done a few problems on a track is trusted primarily by their
# real signal. This is the mechanism that satisfies Case J
# ("actual progress outweighs onboarding self-assessment").
EVIDENCE_HALF_LIFE: float = 2.0

# When the blended effective knowledge for a subject exceeds this
# threshold, the planner treats the subject as *effectively* completed
# for the purposes of subject-DAG unlocking of downstream tracks. This
# lets a self-declared strong learner (Case A3: PF=8 self-assessment)
# progress into Java on day one without waiting to actually finish every
# Programming Fundamentals node.
#
# Not a hard override on the roadmap unlock rule — actual completion
# still governs KB/UI unlocking. This is a planner-only branching
# signal (see planner.py → eligibility.eligible_learning_nodes).
EFFECTIVE_SUBJECT_COMPLETE_THRESHOLD: float = 70.0


@dataclass
class LearnerContext:
    """Everything the adaptive planning pipeline needs to know about ONE learner.

    Populate ONCE at the top of the orchestrator; pass around by
    reference. No layer should ever hold a partial copy — that would
    reintroduce the "one signal missed one code path" bug the bundle
    was designed to eliminate.
    """

    # ---- Onboarding + curriculum baseline -----------------------------------
    onboarding: dict = field(default_factory=dict)

    # ---- Live progress ------------------------------------------------------
    # progress_rows: list ordering matches load_user_progress_rows(); the
    # planner uses this list for unlock/eligibility queries that iterate.
    progress_rows: List[dict] = field(default_factory=list)
    # progress_map: node_id -> row, used for O(1) lookups by ranking and
    # eligibility. Callers can populate either; the property below fills
    # the other on demand.
    progress_map: Dict[str, dict] = field(default_factory=dict)

    # ---- Pacing (interview deadline / capacity) -----------------------------
    pacing_state: dict = field(default_factory=dict)

    # ---- Recent mission history --------------------------------------------
    # All optional; every existing pre-Phase-4 caller path leaves these
    # empty and gets identical scoring to before.
    recent_completions: List[dict] = field(default_factory=list)
    recent_node_ids: List[str] = field(default_factory=list)
    recent_track_ids: List[str] = field(default_factory=list)
    skipped_node_ids: List[str] = field(default_factory=list)
    completed_dates: List[str] = field(default_factory=list)

    # ---- Company targeting --------------------------------------------------
    target_companies: List[str] = field(default_factory=list)

    # ---- Company Intelligence (Phase 2A · additive, planner-inert) ----------
    # Normalized company-intelligence bundle built from the compiled runtime
    # artifacts (Company Runtime Loader). It TRAVELS ALONGSIDE the planner
    # state for future phases. No scoring / ranking / unlock / readiness code
    # reads it yet, so its presence never changes planner output. Defaults to
    # None so any caller that does not opt in behaves exactly as before.
    company_context: Optional["CompanyContext"] = None

    # ---- Company Intelligence activation (Phase 2B) -------------------------
    # When True AND company_context is present/non-empty, the scoring engine
    # adds the bounded Company Intelligence term. Defaults to False so every
    # existing caller (and every existing test) gets byte-identical scores and
    # the planner transparently falls back to roadmap.company_importance().
    company_intelligence_enabled: bool = False

    # ---- Cross-cut helpers --------------------------------------------------
    # knowledge_rows is a separate view over knowledge (topic-level scores
    # for company-readiness estimation). Kept distinct from progress_rows
    # (node-level) because they serve different math.
    knowledge_rows: List[dict] = field(default_factory=list)
    # skip_node_ids is the RETRY hint from validate_mission — the planner
    # is instructed to avoid re-picking these on a regeneration attempt.
    skip_node_ids: Set[str] = field(default_factory=set)

    # -----------------------------------------------------------------
    # Derived, cached-on-first-access properties
    # -----------------------------------------------------------------

    @property
    def urgency(self) -> float:
        """Interview-deadline pacing pressure (0.0 - 1.0). 0.0 = no pressure."""
        try:
            return float(self.pacing_state.get("urgency", 0.0) or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @property
    def position(self) -> Optional[str]:
        """Learner's declared experience band (student / 0-1 / 1-3 / 3-5 / 5+).

        Consumers must treat this as an opaque tag — never hardcode a
        specific enum value here. ranking.py already does the right
        thing (its fatigue rule keys off a data-driven set), but if a
        new position label appears in onboarding we do not want to
        break scoring: unknown positions receive the default policy.
        """
        return (self.onboarding or {}).get("current_position")

    @property
    def onboarding_scores(self) -> dict:
        """Self-assessment map: track_id -> 0-10. Empty when not declared."""
        return (self.onboarding or {}).get("self_assessment") or {}

    def completed_node_ids(self) -> Set[str]:
        """Node ids that are done for planning purposes.

        A row counts as done when its `status` is one of `completed`,
        `mastered`, or `revision_due` (matches unlock.py + planner.py
        pre-refactor). Cached implicitly since progress_rows is
        immutable once the context is built.
        """
        completed: Set[str] = set()
        for row in self.progress_rows or []:
            if not isinstance(row, dict):
                continue
            status = (row.get("status") or "").lower()
            node_id = row.get("node_id")
            if node_id and status in _COMPLETED_STATUSES:
                completed.add(node_id)
        return completed

    def continuity_chain(self) -> ContinuityChain:
        """Return the learning-continuity breadcrumb built from the
        newest completed learning-node row. Same helper the pre-Phase-4
        planner called inline."""
        return chain_from_history(self.recent_completions or [])

    def has_declared_progress(self) -> bool:
        """Return whether the learner has ANY prior completion or activity.

        Used by cold-start detection to distinguish a genuine first
        session from a returning learner whose knowledge signals happen
        to be low. Recent completions is the strongest evidence of
        past activity; a populated progress_map is a weaker but valid
        signal too (they at least have knowledge_nodes rows).
        """
        if self.recent_completions:
            return True
        return bool(self.completed_node_ids())

    # -----------------------------------------------------------------
    # Phase 4 Step 2 · adaptive-knowledge signals
    # -----------------------------------------------------------------
    # Every helper below is DERIVED, deterministic, and reads only what
    # the context already carries. No new Mongo query, no roadmap
    # mutation.

    def track_completion_count(self, track: Optional[str]) -> int:
        """Return the number of completed learning nodes on ``track``.

        This is the "evidence weight" input to
        :meth:`effective_knowledge_score` — as the learner completes
        more nodes on a track, actual mastery gradually outweighs the
        one-time onboarding self-assessment.
        """
        if not track:
            return 0
        counter: Counter = Counter()
        for row in self.progress_rows or []:
            if not isinstance(row, dict):
                continue
            status = (row.get("status") or "").lower()
            if status not in _COMPLETED_STATUSES:
                continue
            if row.get("track") == track:
                counter[row.get("track")] += 1
        return int(counter.get(track, 0))

    def track_average_mastery(self, track: Optional[str]) -> Optional[float]:
        """Return the mean mastery_percentage across the learner's rows
        on ``track``, or None when no rows exist yet.

        Aggregating at the TRACK level (rather than the single-node
        level) gives a stable subject-wide signal — the scoring model
        needs to reason about "how well does this learner know Java",
        not just "how well does this learner know java.threads.core".
        """
        if not track:
            return None
        masteries: List[float] = []
        for row in self.progress_rows or []:
            if not isinstance(row, dict) or row.get("track") != track:
                continue
            val = row.get("mastery_percentage", row.get("mastery"))
            try:
                masteries.append(float(val))
            except (TypeError, ValueError):
                continue
        if not masteries:
            return None
        return sum(masteries) / len(masteries)

    def mastery_evidence_weight(self, track: Optional[str]) -> float:
        """Return α ∈ [0, 1] for how much to trust actual mastery vs
        self-assessment on ``track``.

        α is a sigmoid-shaped ramp: α = n / (n + EVIDENCE_HALF_LIFE),
        so α(0)=0 (no evidence yet → trust the onboarding declaration),
        α(EVIDENCE_HALF_LIFE)=0.5 (equal blend), α→1 for many
        completions. This shape is DATA-DRIVEN — no hardcoded position
        enum, no company enum.
        """
        n = float(self.track_completion_count(track))
        return n / (n + EVIDENCE_HALF_LIFE) if (n + EVIDENCE_HALF_LIFE) > 0 else 0.0

    def effective_knowledge_score(self, track: Optional[str]) -> float:
        """Return the learner's blended knowledge score on ``track``
        (0-100 scale).

        Blending rule:
            effective = α * actual_mastery + (1 - α) * self_assessment * 10

        where α = :meth:`mastery_evidence_weight` and
        self_assessment is the onboarding slider value on the 0-10
        scale. When actual mastery is missing (no rows yet) the blend
        reduces to pure self-assessment; when many completions exist,
        it approaches pure actual mastery — which is the "actual
        progress gradually outweighs onboarding" behaviour the
        Phase 4 brief calls out.
        """
        alpha = self.mastery_evidence_weight(track)
        mastery = self.track_average_mastery(track)
        self_assessment = self.onboarding_scores.get(track) if track else None
        try:
            self_val = float(self_assessment) * 10.0 if self_assessment is not None else None
        except (TypeError, ValueError):
            self_val = None
        if mastery is None and self_val is None:
            return 0.0
        if mastery is None:
            return max(0.0, min(100.0, self_val or 0.0))
        if self_val is None:
            return max(0.0, min(100.0, mastery))
        return max(0.0, min(100.0, alpha * mastery + (1.0 - alpha) * self_val))

    def effectively_completed_tracks(
        self,
        *,
        threshold: float = EFFECTIVE_SUBJECT_COMPLETE_THRESHOLD,
    ) -> Set[str]:
        """Return the set of track ids the planner treats as effectively
        finished for subject-DAG branching purposes.

        A track qualifies when its effective_knowledge_score meets the
        threshold. Metadata-driven: no hardcoded track list; the loop
        walks whatever tracks the learner has self-assessment scores
        for. Used ONLY inside the planner pipeline — the KB and
        Roadmap views continue to use actual completion for their
        unlock rules.
        """
        result: Set[str] = set()
        seen: Set[str] = set(self.onboarding_scores.keys())
        # Also consider tracks present in progress rows even when
        # onboarding never scored them (rare but possible if the
        # curriculum grows a new track after onboarding).
        for row in self.progress_rows or []:
            track = row.get("track") if isinstance(row, dict) else None
            if track:
                seen.add(track)
        for track in seen:
            if self.effective_knowledge_score(track) >= threshold:
                result.add(track)
        return result

    def virtual_completed_node_ids(
        self,
        *,
        threshold: float = EFFECTIVE_SUBJECT_COMPLETE_THRESHOLD,
    ) -> Set[str]:
        """Return the set of leaf-node ids the planner should treat as
        completed for subject-DAG unlocking.

        The set is derived at call time from
        :meth:`effectively_completed_tracks` — for each qualifying
        track we mark every atomic learning node as virtually complete
        so downstream tracks whose leaf prerequisites live in that
        track become eligible. This is what enables Case A3
        (PF=8 self-assessment => Java eligible on day one) without
        touching the roadmap unlock rules KB/UI depend on.
        """
        # Local import to avoid a cycle at module import time.
        from roadmap import get_roadmap

        effective_tracks = self.effectively_completed_tracks(threshold=threshold)
        if not effective_tracks:
            return set()
        roadmap = get_roadmap()
        ids: Set[str] = set()
        for node in roadmap.get_learning_nodes():
            if node.get("track") in effective_tracks:
                ids.add(node.get("id"))
        return ids

    def recent_topics(self, limit: int = 5) -> List[str]:
        """Return the recent topic ids the learner practised (newest
        last). Feeds ``topic_freshness_penalty`` in the ranker so
        same-topic repetition is avoided even when the node id
        differs across days.
        """
        topics: List[str] = []
        for row in list(self.recent_completions or [])[:limit]:
            if not isinstance(row, dict):
                continue
            topic = row.get("topic") or row.get("topic_id")
            if topic:
                topics.append(topic)
        return topics


def build_learner_context(
    *,
    onboarding: Optional[dict] = None,
    progress_rows: Optional[Iterable[dict]] = None,
    pacing_state: Optional[dict] = None,
    target_companies: Optional[Iterable[str]] = None,
    recent_completions: Optional[Iterable[dict]] = None,
    recent_node_ids: Optional[Iterable[str]] = None,
    recent_track_ids: Optional[Iterable[str]] = None,
    skipped_node_ids: Optional[Iterable[str]] = None,
    completed_dates: Optional[Iterable[str]] = None,
    knowledge_rows: Optional[Iterable[dict]] = None,
    skip_node_ids: Optional[Iterable[str]] = None,
    company_context: Optional["CompanyContext"] = None,
    company_intelligence_enabled: bool = False,
) -> LearnerContext:
    """Assemble a LearnerContext from raw inputs.

    Every argument is optional — callers that pass nothing get a
    LearnerContext that behaves identically to the pre-Phase-4 planner
    when it was invoked with only `user_id + db`. The planner is the
    canonical caller; tests can also build contexts directly.

    Phase 2A: a normalized :class:`CompanyContext` is attached (built from
    ``target_companies`` via the Company Runtime Loader when not supplied
    explicitly). This is ADDITIVE and planner-inert — no scoring path reads
    it, so the recommendation output is unchanged.
    """
    rows = list(progress_rows or [])
    progress_map = {row.get("node_id"): row for row in rows if row.get("node_id")}
    resolved_companies = [str(c) for c in (target_companies or [])]

    if company_context is None:
        # Local import avoids any import cycle at module load time and keeps
        # context.py free of a hard dependency on the loader for pure callers.
        from services.learning_engine.company_context import build_company_context
        company_context = build_company_context(resolved_companies)

    return LearnerContext(
        onboarding=dict(onboarding or {}),
        progress_rows=rows,
        progress_map=progress_map,
        pacing_state=dict(pacing_state or {}),
        target_companies=resolved_companies,
        recent_completions=list(recent_completions or []),
        recent_node_ids=list(recent_node_ids or []),
        recent_track_ids=list(recent_track_ids or []),
        skipped_node_ids=list(skipped_node_ids or []),
        completed_dates=list(completed_dates or []),
        knowledge_rows=list(knowledge_rows or []),
        skip_node_ids=set(skip_node_ids or []),
        company_context=company_context,
        company_intelligence_enabled=bool(company_intelligence_enabled),
    )
