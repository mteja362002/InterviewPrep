"""Signal 5 — Learning Consistency.

Does the learner show up regularly? Streaks, missed days, completion
regularity, and skipped work — all derived from completion-date history
and the recent skipped-node list the planner already tracks.

Metrics emitted:
    * current_streak — consecutive active days ending today or yesterday.
    * active_days_14 / missed_days_14 — activity across the last 14 days.
    * completion_consistency — 0..1 fraction of the last 14 days active.
    * skipped_count — nodes skipped in recent missions (a friction signal).
    * trend — active-days momentum (last 7 vs previous 7).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import timedelta

from .context import LearnerIntelligenceInput
from .metrics import today_utc
from .trend_analysis import classify_trend

_WINDOW_DAYS = 14


@dataclass
class ConsistencyMetrics:
    current_streak: int = 0
    active_days_14: int = 0
    missed_days_14: int = 0
    completion_consistency: float = 0.0
    skipped_count: int = 0
    trend: str = "stable"

    def to_dict(self) -> dict:
        return asdict(self)


def compute_consistency(inp: LearnerIntelligenceInput) -> ConsistencyMetrics:
    """Compute consistency metrics from the active-day set."""
    active_days = inp.active_day_set()
    skipped = len(inp.skipped_node_ids or [])
    if not active_days:
        return ConsistencyMetrics(skipped_count=skipped)

    today = today_utc()

    # Streak: count back from today (or yesterday if today is not yet active
    # so a learner mid-day is not punished) while days remain active.
    anchor = today
    if today not in active_days and (today - timedelta(days=1)) in active_days:
        anchor = today - timedelta(days=1)
    streak = 0
    cursor = anchor
    while cursor in active_days:
        streak += 1
        cursor -= timedelta(days=1)

    active_14 = sum(
        1 for i in range(_WINDOW_DAYS) if (today - timedelta(days=i)) in active_days
    )
    missed_14 = _WINDOW_DAYS - active_14
    consistency = active_14 / float(_WINDOW_DAYS)

    active_last7 = sum(1 for i in range(7) if (today - timedelta(days=i)) in active_days)
    active_prev7 = sum(1 for i in range(7, 14) if (today - timedelta(days=i)) in active_days)
    trend = classify_trend(float(active_last7 - active_prev7), stable_band=0.5, rapid_band=3.0)

    return ConsistencyMetrics(
        current_streak=streak,
        active_days_14=active_14,
        missed_days_14=missed_14,
        completion_consistency=round(consistency, 3),
        skipped_count=skipped,
        trend=trend,
    )
