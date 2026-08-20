"""Signal 4 — Weakness Stability (per track).

A weakness is not a single state. This module differentiates:

    * TEMPORARY  — mild weakness, little revision history (probably a
      normal early-learning dip).
    * PERSISTENT — high weakness that keeps resisting effort (many
      attempts, low mastery).
    * RECOVERED  — weakness is now low but the node went through several
      revision cycles to get there (earned stability).
    * RECURRING  — weakness stays moderate/high DESPITE repeated revision
      cycles (it keeps coming back).

All thresholds are transparent constants over existing row fields
(weakness_score, mastery_percentage, attempts, revision_stage). Deterministic.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict

from .context import LearnerIntelligenceInput
from .metrics import (
    WEAKNESS_PERSISTENT, WEAKNESS_RECOVERED, WEAKNESS_RECURRING,
    WEAKNESS_TEMPORARY, mean, safe_float, safe_int,
)

_HIGH_WEAKNESS = 50.0
_MODERATE_WEAKNESS = 40.0
_LOW_WEAKNESS = 30.0
_LOW_MASTERY = 50.0
_MANY_ATTEMPTS = 3
_MANY_REVISIONS = 3
_SOME_REVISIONS = 2


@dataclass
class TrackWeakness:
    track: str
    state: str
    avg_weakness: float
    avg_mastery: float
    attempts: int
    max_revision_stage: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WeaknessStability:
    by_track: Dict[str, TrackWeakness] = field(default_factory=dict)

    def state_for(self, track: str) -> str:
        tw = self.by_track.get(track)
        return tw.state if tw else ""

    def to_dict(self) -> dict:
        return {t: tw.to_dict() for t, tw in self.by_track.items()}


def _classify(avg_weak: float, avg_mastery: float, attempts: int, max_rev: int) -> str:
    if avg_weak < _LOW_WEAKNESS and max_rev >= _SOME_REVISIONS:
        return WEAKNESS_RECOVERED
    if avg_weak >= _MODERATE_WEAKNESS and max_rev >= _MANY_REVISIONS:
        return WEAKNESS_RECURRING
    if avg_weak >= _HIGH_WEAKNESS and attempts >= _MANY_ATTEMPTS and avg_mastery < _LOW_MASTERY:
        return WEAKNESS_PERSISTENT
    if avg_weak >= _HIGH_WEAKNESS:
        return WEAKNESS_PERSISTENT
    return WEAKNESS_TEMPORARY


def compute_weakness_stability(inp: LearnerIntelligenceInput) -> WeaknessStability:
    """Classify weakness stability for every engaged track."""
    result: Dict[str, TrackWeakness] = {}
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
        avg_weak = mean([safe_float(r.get("weakness_score")) for r in engaged])
        avg_mastery = mean([safe_float(r.get("mastery_percentage", r.get("mastery"))) for r in engaged])
        attempts = sum(safe_int(r.get("attempts")) for r in engaged)
        max_rev = max((safe_int(r.get("revision_stage")) for r in engaged), default=0)
        state = _classify(avg_weak, avg_mastery, attempts, max_rev)
        result[track] = TrackWeakness(
            track=track,
            state=state,
            avg_weakness=round(avg_weak, 2),
            avg_mastery=round(avg_mastery, 2),
            attempts=attempts,
            max_revision_stage=max_rev,
        )
    return WeaknessStability(by_track=result)
