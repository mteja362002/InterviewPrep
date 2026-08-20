"""Signal 10 — Interview Readiness Trend (LEARNER readiness, not company).

A single composite trajectory that answers 'is this learner, overall,
trending toward being interview-ready?' It is deliberately NOT a company
readiness percentage — it is a direction derived from four learner signals:
confidence, knowledge expansion (velocity), retention, and consistency.

Trajectory = majority vote of the four component directions:
    net positive -> UPWARD, net negative -> DECLINING, else STABLE.

A 0..1 ``score`` blends the current magnitude of each component so future
features (Predictive Analytics, Mock Interviews) can consume one number.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List

from .confidence import ConfidenceTrend
from .consistency import ConsistencyMetrics
from .metrics import (
    NEGATIVE_TRENDS, POSITIVE_TRENDS, STABLE, UPWARD, DOWNWARD, clamp, mean,
)
from .retention import RetentionMetrics
from .velocity import VelocityMetrics


@dataclass
class ReadinessTrend:
    trajectory: str = STABLE
    score: float = 0.0
    net_votes: int = 0
    components: Dict[str, str] = field(default_factory=dict)
    signals: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _vote(direction: str) -> int:
    if direction in POSITIVE_TRENDS:
        return 1
    if direction in NEGATIVE_TRENDS:
        return -1
    return 0


def compute_readiness_trend(
    velocity: VelocityMetrics,
    confidence: ConfidenceTrend,
    retention: RetentionMetrics,
    consistency: ConsistencyMetrics,
) -> ReadinessTrend:
    """Blend the four learner signals into one readiness trajectory."""
    components = {
        "confidence": confidence.direction,
        "knowledge_expansion": velocity.trend,
        "retention": retention.trend,
        "consistency": consistency.trend,
    }
    net = sum(_vote(d) for d in components.values())

    if net >= 1:
        trajectory = UPWARD
    elif net <= -1:
        trajectory = DOWNWARD
    else:
        trajectory = STABLE

    score = clamp(
        mean([
            confidence.current_avg / 10.0,
            velocity.speed_score,
            retention.knowledge_stability,
            consistency.completion_consistency,
        ]),
        0.0, 1.0,
    )

    signals: List[str] = []
    if confidence.direction in POSITIVE_TRENDS:
        signals.append("confidence improving")
    if velocity.trend in POSITIVE_TRENDS:
        signals.append("knowledge expanding")
    if retention.trend in POSITIVE_TRENDS:
        signals.append("revision improving")
    if consistency.trend in POSITIVE_TRENDS:
        signals.append("consistency improving")

    return ReadinessTrend(
        trajectory=trajectory,
        score=round(score, 3),
        net_votes=net,
        components=components,
        signals=signals,
    )
