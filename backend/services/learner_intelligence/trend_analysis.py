"""Deterministic trend analysis for time-ordered numeric series.

The Learner Intelligence Engine never uses regression models, ML, or
randomness. Trend detection here is a transparent, reproducible
'split-mean delta': compare the mean of the RECENT half of a chronological
series to the mean of the OLDER half. The sign and magnitude of that delta
map onto the canonical trend vocabulary in :mod:`metrics`.

Why split-mean and not a slope fit?
    * Zero dependencies, O(n), fully explainable ('recent 3 vs older 3').
    * Robust to a single outlier compared with a two-point delta.
    * Deterministic: same series in => same label out, always.
"""
from __future__ import annotations

from typing import List, Sequence, Tuple

from .metrics import (
    DECLINING, INCREASING, RAPID_DECLINE, RAPID_IMPROVEMENT, STABLE, mean,
)


def split_mean_delta(series: Sequence[float]) -> float:
    """Return (mean of recent half) - (mean of older half).

    A chronological series (oldest first) is split in two. With an odd
    length the middle sample is included in the RECENT half so the newest
    observation always carries weight. Series shorter than 2 yield 0.0
    (no discernible trend).
    """
    values = [float(v) for v in series if v is not None]
    n = len(values)
    if n < 2:
        return 0.0
    mid = n // 2
    older = values[:mid]
    recent = values[mid:]
    return mean(recent) - mean(older)


def classify_trend(
    delta: float,
    *,
    stable_band: float = 0.5,
    rapid_band: float = 3.0,
) -> str:
    """Map a numeric delta onto the canonical trend vocabulary.

    * |delta| within ``stable_band``      -> STABLE
    * delta beyond +``rapid_band``        -> RAPID_IMPROVEMENT
    * delta beyond -``rapid_band``        -> RAPID_DECLINE
    * otherwise positive                  -> INCREASING
    * otherwise negative                  -> DECLINING
    """
    if delta >= rapid_band:
        return RAPID_IMPROVEMENT
    if delta <= -rapid_band:
        return RAPID_DECLINE
    if delta > stable_band:
        return INCREASING
    if delta < -stable_band:
        return DECLINING
    return STABLE


def classify_series(
    series: Sequence[float],
    *,
    stable_band: float = 0.5,
    rapid_band: float = 3.0,
) -> Tuple[float, str]:
    """Convenience: return (delta, label) for a chronological series."""
    delta = split_mean_delta(series)
    return delta, classify_trend(delta, stable_band=stable_band, rapid_band=rapid_band)
