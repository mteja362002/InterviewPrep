"""LearnerIntelligenceUpdate — the canonical learner-state change record (Phase 3B).

A deterministic translation of ONE immutable ``AssessmentEvidence`` into the
learner-state changes Learner Intelligence recognizes. It carries ONLY
learner-state fields (confidence / mastery / weakness / strength /
knowledge-gap / revision hints / signals / history) plus explainable
metadata — never planner-specific fields.

Records are immutable (frozen) and persisted append-only, forming the
learner-evidence history future analytics will consume.
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


@dataclass(frozen=True)
class LearnerIntelligenceUpdate:
    """Immutable learner-state delta derived from assessment evidence."""

    user_id: Optional[str]
    assessment_id: Optional[str]
    assessment_type: Optional[str]
    roadmap_node_id: Optional[str]

    # ---- learner-state changes (NOT planner fields) --------------------
    confidence_delta: float
    mastery_delta: float
    weakness_detected: bool
    strength_detected: bool
    knowledge_gap_adjustment: float
    revision_hint: bool

    # ---- signals + explainability + provenance -------------------------
    learning_signals: Dict = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)

    update_id: str = field(default_factory=_uuid)
    source: str = "assessment_evidence"
    evidence_schema_version: Optional[str] = None
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, doc: dict) -> "LearnerIntelligenceUpdate":
        """Rebuild from a persisted document (ignores Mongo _id / extras)."""
        allowed = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in (doc or {}).items() if k in allowed})
