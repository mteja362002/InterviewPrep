"""Signal 7 — Coding Growth.

How is the learner progressing on hands-on coding practice? Coding activity
is inferred from existing row fields — nodes the learner has actually
attempted (``attempts`` > 0) or spent solve-time on — combined with the
roadmap's authored ``difficulty`` for each node.

NOTE: PrepOS does not (yet) persist a per-submission acceptance log as a
separate collection, so acceptance/pattern trends are derived from the
mastery signal on attempted coding nodes — a deterministic proxy. When no
coding activity exists, ``has_signal`` is False and the planner ignores this
signal. This is a documented extension point for Phase 3.

Metrics emitted:
    * solved_count — attempted coding nodes now completed/mastered.
    * difficulty_progression — hardest difficulty the learner has solved.
    * acceptance_trend — mastery trend across attempted coding nodes.
    * repeated_mistakes — many attempts, low mastery.
    * avg_attempts — mean attempts per attempted coding node.
    * has_signal — whether any coding activity was observed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import List, Optional

from .context import LearnerIntelligenceInput
from .metrics import (
    COMPLETED_STATUSES, STABLE, mean, safe_float, safe_int,
)
from .trend_analysis import classify_trend, split_mean_delta

_DIFFICULTY_ORDINAL = {"easy": 0, "medium": 1, "hard": 2}
_ORDINAL_DIFFICULTY = {0: "easy", 1: "medium", 2: "hard"}
_SOLVED_MASTERY = 60.0
_REPEATED_ATTEMPTS = 3
_LOW_MASTERY = 60.0


@dataclass
class CodingGrowth:
    solved_count: int = 0
    difficulty_progression: str = "none"
    acceptance_trend: str = STABLE
    repeated_mistakes: int = 0
    avg_attempts: float = 0.0
    has_signal: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def _mastery(row: dict) -> float:
    return safe_float(row.get("mastery_percentage", row.get("mastery")))


def _coding_rows(inp: LearnerIntelligenceInput) -> List[dict]:
    """Rows that reflect hands-on coding practice — attempted or timed."""
    out = []
    for r in inp.progress_rows or []:
        if not isinstance(r, dict):
            continue
        if safe_int(r.get("attempts")) > 0 or safe_float(r.get("actual_solve_minutes")) > 0:
            out.append(r)
    return out


def _difficulty_of(row: dict) -> Optional[int]:
    diff = (row.get("difficulty") or "").lower()
    return _DIFFICULTY_ORDINAL.get(diff)


def compute_coding_growth(inp: LearnerIntelligenceInput) -> CodingGrowth:
    """Compute coding-growth metrics from attempted coding nodes."""
    rows = _coding_rows(inp)
    if not rows:
        return CodingGrowth()

    solved = [
        r for r in rows
        if (r.get("status") or "").lower() in COMPLETED_STATUSES or _mastery(r) >= _SOLVED_MASTERY
    ]

    # Hardest difficulty actually solved (roadmap-authored ordinal).
    solved_ordinals = [d for d in (_difficulty_of(r) for r in solved) if d is not None]
    progression = _ORDINAL_DIFFICULTY.get(max(solved_ordinals), "none") if solved_ordinals else "none"

    # Acceptance trend: mastery series ordered by attempts (later attempts =
    # more recent practice) — deterministic proxy for improving acceptance.
    rows_by_attempts = sorted(rows, key=lambda r: safe_int(r.get("attempts")))
    mastery_series = [_mastery(r) for r in rows_by_attempts]
    acceptance_trend = classify_trend(
        split_mean_delta(mastery_series), stable_band=3.0, rapid_band=15.0,
    )

    repeated = sum(
        1 for r in rows
        if safe_int(r.get("attempts")) >= _REPEATED_ATTEMPTS and _mastery(r) < _LOW_MASTERY
    )
    avg_attempts = mean([safe_int(r.get("attempts")) for r in rows])

    return CodingGrowth(
        solved_count=len(solved),
        difficulty_progression=progression,
        acceptance_trend=acceptance_trend,
        repeated_mistakes=repeated,
        avg_attempts=round(avg_attempts, 2),
        has_signal=True,
    )
