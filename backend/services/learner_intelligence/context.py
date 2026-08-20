"""LearnerIntelligenceInput — the immutable bundle of raw learner signals the
Learner Intelligence computation pipeline consumes.

This mirrors the design philosophy of
:class:`services.learning_engine.context.LearnerContext`: ONE pure data
bundle, populated once, read-only downstream. It never touches Mongo and
never fetches roadmap nodes — the planner (or any future analytics / AI
Mentor caller) is responsible for handing it the rows it already loaded.

Everything is derived from EXISTING collections (``knowledge_nodes`` progress
rows + the recent-mission history the planner already assembles). No new
store is introduced.

Design contract:
    * PURE data + cheap derived accessors. No side effects.
    * OPTIONAL everywhere: an empty input yields an empty (is_empty)
      snapshot, and the planner falls back to its pre-2C behaviour.
    * DETERMINISTIC: accessors sort / group the same way every call.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Iterable, List, Optional

from .metrics import (
    COMPLETED_STATUSES, parse_date, safe_float, safe_int,
)


@dataclass
class LearnerIntelligenceInput:
    """Raw learner signals for ONE learner, ready for the compute pipeline.

    Fields map 1:1 onto data the adaptive planner already has in hand:

    * ``progress_rows`` — canonical ``knowledge_nodes`` rows (confidence,
      mastery_percentage, weakness_score, status, attempts, revision_stage,
      next_revision, completion_date, track, …).
    * ``recent_completions`` — recently completed rows, NEWEST FIRST (the
      same list the planner builds for continuity).
    * ``completed_dates`` — every completion date string in history; the
      sole basis for velocity / consistency (kept separate from
      recent_completions because it can be a longer, lighter list).
    * ``recent_track_ids`` — tracks touched by recent missions.
    * ``skipped_node_ids`` — nodes skipped in recent missions.
    * ``position`` — declared experience band (opaque tag; never branched
      on by identity).
    """

    progress_rows: List[dict] = field(default_factory=list)
    recent_completions: List[dict] = field(default_factory=list)
    completed_dates: List[str] = field(default_factory=list)
    recent_track_ids: List[str] = field(default_factory=list)
    skipped_node_ids: List[str] = field(default_factory=list)
    position: Optional[str] = None

    # ---- derived, cheap, deterministic accessors ------------------------ #

    def has_any_signal(self) -> bool:
        """True when there is at least one progress row or completion date —
        i.e. enough to compute *something*. When False the engine returns an
        empty snapshot and the planner falls back."""
        return bool(self.progress_rows) or bool(self.completed_dates)

    def completion_dates(self) -> List[date]:
        """All parseable completion dates, ascending. Drives velocity and
        consistency. Deduplication is intentionally NOT done — multiple
        completions on one day legitimately signal higher velocity."""
        parsed = [parse_date(d) for d in (self.completed_dates or [])]
        return sorted([d for d in parsed if d is not None])

    def active_day_set(self) -> set:
        """Distinct calendar days with at least one completion (for streaks /
        consistency, where a day is either active or not)."""
        return set(self.completion_dates())

    def rows_by_track(self) -> Dict[str, List[dict]]:
        """Group progress rows by their ``track``. Rows without a track are
        grouped under the empty string and ignored by track-level signals."""
        grouped: Dict[str, List[dict]] = {}
        for row in self.progress_rows or []:
            if not isinstance(row, dict):
                continue
            track = row.get("track") or ""
            grouped.setdefault(track, []).append(row)
        return grouped

    def engaged_rows(self) -> List[dict]:
        """Rows the learner has actually engaged with (not a pure cold-start
        seed): any completed status, or attempts / revision activity."""
        out: List[dict] = []
        for row in self.progress_rows or []:
            if not isinstance(row, dict):
                continue
            status = (row.get("status") or "").lower()
            if (
                status in COMPLETED_STATUSES
                or status == "in_progress"
                or safe_int(row.get("attempts")) > 0
                or safe_int(row.get("revision_stage")) > 0
            ):
                out.append(row)
        return out

    def confidence_series(self) -> List[float]:
        """Confidence values ordered oldest -> newest by completion date.

        Built from ``recent_completions`` (which carry completion_date and
        confidence). This chronological series is the basis for the
        confidence trend. Rows without a completion date sort last.
        """
        dated = [
            r for r in (self.recent_completions or [])
            if isinstance(r, dict) and r.get("completion_date") is not None
        ]
        dated.sort(key=lambda r: str(r.get("completion_date") or ""))
        return [safe_float(r.get("confidence")) for r in dated]


def build_learner_intelligence_input(
    *,
    progress_rows: Optional[Iterable[dict]] = None,
    recent_completions: Optional[Iterable[dict]] = None,
    completed_dates: Optional[Iterable[str]] = None,
    recent_track_ids: Optional[Iterable[str]] = None,
    skipped_node_ids: Optional[Iterable[str]] = None,
    position: Optional[str] = None,
) -> LearnerIntelligenceInput:
    """Assemble a :class:`LearnerIntelligenceInput` from raw iterables.

    Every argument is optional; omitting them yields an input whose
    ``has_any_signal()`` is False, which the engine turns into an empty
    snapshot (planner fallback). Never raises.
    """
    return LearnerIntelligenceInput(
        progress_rows=[r for r in (progress_rows or []) if isinstance(r, dict)],
        recent_completions=[r for r in (recent_completions or []) if isinstance(r, dict)],
        completed_dates=[str(d) for d in (completed_dates or []) if d],
        recent_track_ids=[str(t) for t in (recent_track_ids or []) if t],
        skipped_node_ids=[str(n) for n in (skipped_node_ids or []) if n],
        position=position,
    )
