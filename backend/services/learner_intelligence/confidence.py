"""Signal 3 — Confidence Trend.

Static confidence is already known to the planner. This module adds the
missing dimension: is the learner's confidence RISING or FALLING over time?
Computed from the chronological confidence series of recent completions via
the deterministic split-mean delta.

Metrics emitted:
    * current_avg — mean confidence across all engaged rows (0..10).
    * recent_avg — mean confidence of the most recent completions.
    * delta — split-mean change over the chronological series.
    * direction — canonical trend label.
    * low_confidence_count — engaged rows below the weak threshold.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .context import LearnerIntelligenceInput
from .metrics import STABLE, mean, safe_float
from .trend_analysis import classify_trend, split_mean_delta

_WEAK_CONFIDENCE = 4.0
_RECENT_WINDOW = 5


@dataclass
class ConfidenceTrend:
    current_avg: float = 0.0
    recent_avg: float = 0.0
    delta: float = 0.0
    direction: str = STABLE
    low_confidence_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def compute_confidence_trend(inp: LearnerIntelligenceInput) -> ConfidenceTrend:
    """Compute the confidence trend from the chronological confidence series."""
    series = inp.confidence_series()
    all_conf = [
        safe_float(r.get("confidence"))
        for r in (inp.progress_rows or [])
        if isinstance(r, dict) and r.get("confidence") is not None
    ]

    if not series and not all_conf:
        return ConfidenceTrend()

    # Confidence lives on a 0..10 slider, so the bands are tighter than the
    # generic velocity bands: a 2-point swing is already "rapid".
    delta = split_mean_delta(series)
    direction = classify_trend(delta, stable_band=0.4, rapid_band=2.0)

    recent_avg = mean(series[-_RECENT_WINDOW:]) if series else mean(all_conf)
    current_avg = mean(all_conf) if all_conf else recent_avg
    low = sum(1 for c in all_conf if c < _WEAK_CONFIDENCE)

    return ConfidenceTrend(
        current_avg=round(current_avg, 2),
        recent_avg=round(recent_avg, 2),
        delta=round(delta, 2),
        direction=direction,
        low_confidence_count=low,
    )
