"""Signal 1 — Learning Velocity.

How fast is THIS learner moving through the curriculum, and is that speed
rising or falling? Derived purely from completion-date history (no new
store). Deterministic for a fixed 'today'.

Metrics emitted:
    * topics_last_7 / topics_prev_7 — completions in the two most recent
      7-day windows (the basis for the speed trend).
    * avg_topics_per_week — lifetime average over the active span.
    * completions_total — total completions observed.
    * trend — canonical trend label for learning speed.
    * speed_score — 0..1 normalized pace (used by the planner adapter and
      the readiness composite).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .context import LearnerIntelligenceInput
from .metrics import clamp, today_utc
from .trend_analysis import classify_trend

# A learner completing ~7 topics/week is treated as a full-speed (1.0)
# pace anchor. This is a transparent normalization constant, NOT a target
# or prediction.
_FULL_SPEED_TOPICS_PER_WEEK = 7.0


@dataclass
class VelocityMetrics:
    topics_last_7: int = 0
    topics_prev_7: int = 0
    avg_topics_per_week: float = 0.0
    completions_total: int = 0
    trend: str = "stable"
    speed_score: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def compute_velocity(inp: LearnerIntelligenceInput) -> VelocityMetrics:
    """Compute learning-velocity metrics from completion history."""
    dates = inp.completion_dates()
    if not dates:
        return VelocityMetrics()

    today = today_utc()
    last_7 = sum(1 for d in dates if 0 <= (today - d).days < 7)
    prev_7 = sum(1 for d in dates if 7 <= (today - d).days < 14)

    span_days = max(1, (today - min(dates)).days + 1)
    weeks = max(1.0, span_days / 7.0)
    avg_per_week = len(dates) / weeks

    # Speed trend compares the two recent windows directly (deterministic).
    trend = classify_trend(float(last_7 - prev_7), stable_band=0.5, rapid_band=3.0)
    speed_score = clamp(avg_per_week / _FULL_SPEED_TOPICS_PER_WEEK, 0.0, 1.0)

    return VelocityMetrics(
        topics_last_7=last_7,
        topics_prev_7=prev_7,
        avg_topics_per_week=round(avg_per_week, 2),
        completions_total=len(dates),
        trend=trend,
        speed_score=round(speed_score, 3),
    )
