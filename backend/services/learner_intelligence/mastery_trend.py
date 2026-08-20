"""Signal 8 — Topic Mastery Trend (per track).

Binary 'mastered / not' is too coarse. This module classifies each engaged
track into a trajectory state:

    * MASTERED   — avg mastery is very high.
    * REGRESSING — weakness rising and multiple revision cycles — losing
      ground despite effort.
    * PLATEAU    — mid mastery with NO recent activity on the track.
    * IMPROVING  — mid mastery with recent activity (actively climbing).
    * LEARNING   — early / low mastery, just getting started.

Derived from existing row fields + completion recency. Deterministic.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict

from .context import LearnerIntelligenceInput
from .metrics import (
    MASTERY_IMPROVING, MASTERY_LEARNING, MASTERY_MASTERED, MASTERY_PLATEAU,
    MASTERY_REGRESSING, mean, parse_date, safe_float, safe_int, today_utc,
)

_MASTERED = 90.0
_MID = 40.0
_REGRESS_WEAKNESS = 45.0
_RECENT_DAYS = 10
_SOME_REVISIONS = 2


@dataclass
class TrackMasteryTrend:
    track: str
    state: str
    avg_mastery: float
    avg_weakness: float
    recent_activity: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MasteryTrends:
    by_track: Dict[str, TrackMasteryTrend] = field(default_factory=dict)

    def state_for(self, track: str) -> str:
        t = self.by_track.get(track)
        return t.state if t else ""

    def to_dict(self) -> dict:
        return {t: mt.to_dict() for t, mt in self.by_track.items()}


def _has_recent_activity(rows, today) -> bool:
    for r in rows:
        d = parse_date(r.get("completion_date"))
        if d is not None and 0 <= (today - d).days <= _RECENT_DAYS:
            return True
    return False


def _classify(avg_mastery: float, avg_weak: float, max_rev: int, recent: bool) -> str:
    if avg_mastery >= _MASTERED:
        return MASTERY_MASTERED
    if avg_weak >= _REGRESS_WEAKNESS and max_rev >= _SOME_REVISIONS:
        return MASTERY_REGRESSING
    if avg_mastery >= _MID and not recent:
        return MASTERY_PLATEAU
    if avg_mastery >= _MID and recent:
        return MASTERY_IMPROVING
    return MASTERY_LEARNING


def compute_mastery_trends(inp: LearnerIntelligenceInput) -> MasteryTrends:
    """Classify the mastery trajectory for every engaged track."""
    today = today_utc()
    result: Dict[str, TrackMasteryTrend] = {}
    for track, rows in inp.rows_by_track().items():
        if not track:
            continue
        engaged = [
            r for r in rows
            if (r.get("status") or "").lower() != "not_started"
            or safe_int(r.get("attempts")) > 0
            or safe_int(r.get("revision_stage")) > 0
        ]
        if not engaged:
            continue
        avg_mastery = mean([safe_float(r.get("mastery_percentage", r.get("mastery"))) for r in engaged])
        avg_weak = mean([safe_float(r.get("weakness_score")) for r in engaged])
        max_rev = max((safe_int(r.get("revision_stage")) for r in engaged), default=0)
        recent = _has_recent_activity(engaged, today)
        state = _classify(avg_mastery, avg_weak, max_rev, recent)
        result[track] = TrackMasteryTrend(
            track=track,
            state=state,
            avg_mastery=round(avg_mastery, 2),
            avg_weakness=round(avg_weak, 2),
            recent_activity=recent,
        )
    return MasteryTrends(by_track=result)
