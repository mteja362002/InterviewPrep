"""Signal 9 — Difficulty Adaptation.

Recommends whether the learner should MAINTAIN, INCREASE, or DECREASE
difficulty — WITHOUT ever reordering the roadmap. It is advisory guidance
the planner adapter turns into a bounded scoring nudge (e.g. deprioritise a
'hard' candidate when the learner is struggling).

The decision is a transparent vote over already-computed signals:

    Struggling votes:   declining confidence, poor retention, many
                        repeated mistakes.
    Progressing votes:  rising confidence, rising velocity, high
                        knowledge stability.

More struggling  -> DECREASE
More progressing -> INCREASE
Balanced / weak evidence -> MAINTAIN
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import List

from .confidence import ConfidenceTrend
from .metrics import (
    DIFFICULTY_DECREASE, DIFFICULTY_INCREASE, DIFFICULTY_MAINTAIN,
    NEGATIVE_TRENDS, POSITIVE_TRENDS,
)
from .retention import RetentionMetrics
from .velocity import VelocityMetrics

_POOR_RETENTION = 0.5
_STRONG_STABILITY = 0.7
_MANY_REPEATED = 3


@dataclass
class DifficultyAdaptation:
    action: str = DIFFICULTY_MAINTAIN
    struggling_votes: int = 0
    progressing_votes: int = 0
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def compute_difficulty_adaptation(
    velocity: VelocityMetrics,
    confidence: ConfidenceTrend,
    retention: RetentionMetrics,
) -> DifficultyAdaptation:
    """Vote over confidence / retention / velocity to recommend an action."""
    reasons: List[str] = []
    struggling = 0
    progressing = 0

    if confidence.direction in NEGATIVE_TRENDS:
        struggling += 1
        reasons.append("confidence declining")
    elif confidence.direction in POSITIVE_TRENDS:
        progressing += 1
        reasons.append("confidence improving")

    if retention.revised_count > 0 and retention.revision_success_rate < _POOR_RETENTION:
        struggling += 1
        reasons.append("low revision success")
    if retention.repeated_mistakes >= _MANY_REPEATED:
        struggling += 1
        reasons.append("repeated mistakes")
    if retention.knowledge_stability >= _STRONG_STABILITY:
        progressing += 1
        reasons.append("stable knowledge")

    if velocity.trend in POSITIVE_TRENDS:
        progressing += 1
        reasons.append("velocity rising")
    elif velocity.trend in NEGATIVE_TRENDS:
        struggling += 1
        reasons.append("velocity slowing")

    if struggling >= 2 and struggling > progressing:
        action = DIFFICULTY_DECREASE
    elif progressing >= 2 and progressing > struggling:
        action = DIFFICULTY_INCREASE
    else:
        action = DIFFICULTY_MAINTAIN

    return DifficultyAdaptation(
        action=action,
        struggling_votes=struggling,
        progressing_votes=progressing,
        reasons=reasons,
    )
