"""Signal 2 — Retention Quality.

Does learned material STICK? Uses revision outcomes and repeated mistakes
recorded on the canonical ``knowledge_nodes`` rows. A node that has entered
the spaced-repetition schedule (revision_stage > 0) and still holds solid
confidence is a retention SUCCESS; one that keeps needing attempts with low
mastery is a repeated mistake.

Metrics emitted:
    * revised_count / revision_successes / revision_failures.
    * revision_success_rate — 0..1.
    * repeated_mistakes — nodes with many attempts but low mastery.
    * knowledge_stability — 0..1 (mean mastery of revised nodes).
    * trend — confidence trend among revised nodes (proxy for whether
      retention is improving or decaying).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .context import LearnerIntelligenceInput
from .metrics import STABLE, clamp, mean, safe_float, safe_int
from .trend_analysis import classify_trend, split_mean_delta

_RETAINED_CONFIDENCE = 6.0     # confidence at/above this on a revised node = retained
_REPEATED_ATTEMPTS = 3         # attempts at/above this ...
_LOW_MASTERY = 60.0            # ... combined with mastery below this = repeated mistake


@dataclass
class RetentionMetrics:
    revised_count: int = 0
    revision_successes: int = 0
    revision_failures: int = 0
    revision_success_rate: float = 0.0
    repeated_mistakes: int = 0
    knowledge_stability: float = 0.0
    trend: str = STABLE

    def to_dict(self) -> dict:
        return asdict(self)


def _mastery(row: dict) -> float:
    return safe_float(row.get("mastery_percentage", row.get("mastery")))


def compute_retention(inp: LearnerIntelligenceInput) -> RetentionMetrics:
    """Compute retention-quality metrics from progress rows."""
    rows = inp.progress_rows or []
    if not rows:
        return RetentionMetrics()

    revised = [r for r in rows if safe_int(r.get("revision_stage")) > 0]
    successes = sum(1 for r in revised if safe_float(r.get("confidence")) >= _RETAINED_CONFIDENCE)
    failures = len(revised) - successes
    success_rate = successes / len(revised) if revised else 0.0

    repeated = sum(
        1 for r in rows
        if safe_int(r.get("attempts")) >= _REPEATED_ATTEMPTS and _mastery(r) < _LOW_MASTERY
    )

    stability = clamp(mean([_mastery(r) for r in revised]) / 100.0, 0.0, 1.0) if revised else 0.0

    # Retention trend: are revised nodes gaining or losing confidence? Ordered
    # by the revision schedule so "recent" means later in the spaced sequence.
    revised_sorted = sorted(revised, key=lambda r: safe_int(r.get("revision_stage")))
    conf_series = [safe_float(r.get("confidence")) for r in revised_sorted]
    trend = classify_trend(split_mean_delta(conf_series), stable_band=0.4, rapid_band=2.0)

    return RetentionMetrics(
        revised_count=len(revised),
        revision_successes=successes,
        revision_failures=failures,
        revision_success_rate=round(success_rate, 3),
        repeated_mistakes=repeated,
        knowledge_stability=round(stability, 3),
        trend=trend,
    )
