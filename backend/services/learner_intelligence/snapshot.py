"""LearnerIntelligenceSnapshot — the single, lightweight, precomputed view of
how ONE learner learns.

This is the artifact the planner (and future Analytics / AI Mentor / Mock
Interview features) consume. It is produced ONCE by :mod:`engine` and then
read-only — exactly the 'compute once, consume many' separation the Phase 2C
brief calls for. It carries no behaviour beyond convenience accessors and
serialization.

An ``is_empty`` snapshot (no learner signal available) is the fallback
sentinel: the planner detects it and behaves exactly as it did before
Phase 2C.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .coding import CodingGrowth
from .confidence import ConfidenceTrend
from .consistency import ConsistencyMetrics
from .difficulty import DifficultyAdaptation
from .mastery_trend import MasteryTrends
from .metrics import DIFFICULTY_MAINTAIN
from .readiness import ReadinessTrend
from .retention import RetentionMetrics
from .revision_health import RevisionHealth
from .velocity import VelocityMetrics
from .weakness import WeaknessStability


@dataclass
class LearnerIntelligenceSnapshot:
    """Aggregate of all ten learner-intelligence signals.

    ``empty`` marks a snapshot built with insufficient data — consumers
    MUST treat it as 'no learner intelligence available' and fall back.
    """

    velocity: VelocityMetrics = field(default_factory=VelocityMetrics)
    retention: RetentionMetrics = field(default_factory=RetentionMetrics)
    confidence_trend: ConfidenceTrend = field(default_factory=ConfidenceTrend)
    consistency: ConsistencyMetrics = field(default_factory=ConsistencyMetrics)
    revision_health: RevisionHealth = field(default_factory=RevisionHealth)
    weakness_stability: WeaknessStability = field(default_factory=WeaknessStability)
    mastery_trends: MasteryTrends = field(default_factory=MasteryTrends)
    coding_growth: CodingGrowth = field(default_factory=CodingGrowth)
    difficulty_adaptation: DifficultyAdaptation = field(default_factory=DifficultyAdaptation)
    readiness_trend: ReadinessTrend = field(default_factory=ReadinessTrend)

    empty: bool = True

    @property
    def is_empty(self) -> bool:
        return self.empty

    def weakness_state(self, track: Optional[str]) -> str:
        return self.weakness_stability.state_for(track) if track else ""

    def mastery_state(self, track: Optional[str]) -> str:
        return self.mastery_trends.state_for(track) if track else ""

    def to_dict(self) -> dict:
        """Full serialization — for analytics endpoints, AI Mentor context,
        and debugging. Deterministic and JSON-safe."""
        return {
            "empty": self.empty,
            "velocity": self.velocity.to_dict(),
            "retention": self.retention.to_dict(),
            "confidence_trend": self.confidence_trend.to_dict(),
            "consistency": self.consistency.to_dict(),
            "revision_health": self.revision_health.to_dict(),
            "weakness_stability": self.weakness_stability.to_dict(),
            "mastery_trends": self.mastery_trends.to_dict(),
            "coding_growth": self.coding_growth.to_dict(),
            "difficulty_adaptation": self.difficulty_adaptation.to_dict(),
            "readiness_trend": self.readiness_trend.to_dict(),
        }


def empty_snapshot() -> LearnerIntelligenceSnapshot:
    """Return the canonical empty snapshot (planner fallback sentinel)."""
    return LearnerIntelligenceSnapshot(empty=True)
