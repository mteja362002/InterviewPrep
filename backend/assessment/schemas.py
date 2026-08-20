"""Assessment Engine — domain schemas & vocabulary (Phase 3A).

First-class domain objects for the reusable Assessment Platform. Pure data +
enums; no I/O, no LLM, deterministic. Pydantic v2 models double as API
contracts and (via ``model_dump``) as the normalized ``assessments`` Mongo
document shape.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


class AssessmentType(str, Enum):
    CODING = "coding"
    THEORY = "theory"
    MCQ = "mcq"
    DEBUGGING = "debugging"
    BEHAVIORAL = "behavioral"
    SYSTEM_DESIGN = "system_design"
    RESUME = "resume"
    PROJECT_EXPLANATION = "project_explanation"


class AssessmentStatus(str, Enum):
    PENDING = "pending"
    STARTED = "started"
    SUBMITTED = "submitted"
    EVALUATED = "evaluated"
    COMPLETED = "completed"


class Verdict(str, Enum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    PARTIALLY_CORRECT = "partially_correct"


class RubricDimension(BaseModel):
    key: str
    label: str
    weight: float  # 0..1, dimensions sum to 1.0
    description: str = ""


class Rubric(BaseModel):
    rubric_id: str
    assessment_type: AssessmentType
    dimensions: List[RubricDimension]


class Question(BaseModel):
    """Generated assessment question. For coding, reuses problem_bank
    metadata (by reference — problem_id) rather than duplicating it."""
    question_id: str = Field(default_factory=_uuid)
    prompt: str = ""
    problem_id: Optional[str] = None          # problem_bank stable id (e.g. lc-3)
    leetcode_id: Optional[int] = None
    title: Optional[str] = None
    difficulty: Optional[str] = None
    pattern: Optional[str] = None
    estimated_minutes: Optional[int] = None
    external_url: Optional[str] = None
    expected_time_complexity: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class Attempt(BaseModel):
    """The learner's submitted attempt (deterministic, structured inputs)."""
    attempt_id: str = Field(default_factory=_uuid)
    submitted_at: str = Field(default_factory=_now_iso)
    passed_tests: int = 0
    total_tests: int = 0
    edge_cases_passed: int = 0
    edge_cases_total: int = 0
    claimed_time_complexity: Optional[str] = None
    time_taken_seconds: Optional[int] = None
    explanation: Optional[str] = None
    code: Optional[str] = None
    solved: Optional[bool] = None
    metadata: dict = Field(default_factory=dict)


class DimensionScore(BaseModel):
    key: str
    label: str
    score: float          # 0..100
    weight: float
    detail: str = ""


class Result(BaseModel):
    verdict: Verdict
    overall_score: float           # 0..100 weighted
    dimension_scores: List[DimensionScore] = Field(default_factory=list)
    complexity_rating: Optional[str] = None   # optimal | suboptimal | unknown
    edge_case_coverage: float = 0.0           # 0..1
    completion_status: str = "completed"
    evaluated_at: str = Field(default_factory=_now_iso)


class Feedback(BaseModel):
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    missing_concepts: List[str] = Field(default_factory=list)
    revision_recommendation: Optional[str] = None
    difficulty_recommendation: str = "maintain"  # maintain | increase | decrease
    confidence_impact: str = "neutral"           # positive | neutral | negative


EVIDENCE_SCHEMA_VERSION = "1.0"


class AssessmentEvidence(BaseModel):
    """THE single canonical Assessment Evidence contract (Phase 3A+).

    This is the ONE object every assessment type produces and every future
    consumer (Learner Intelligence, Planner, Analytics, Revision Engine, AI
    Mentor, Company Readiness) reads — WITHOUT any assessment-type-specific
    logic. To stay type-agnostic it exposes:

      * Canonical NORMALIZED scalars (all 0..1, or -1..1 for the delta):
        ``accuracy``, ``proficiency``, ``completion_quality``,
        ``confidence_delta``.
      * Canonical BOOLEAN signals: ``weakness_confirmation``,
        ``revision_trigger``, ``repeated_mistakes`` (also mirrored in
        ``signals`` for uniform dict access).
      * An open ``metrics`` bag for type-specific normalized detail (e.g.
        coding edge-case coverage, MCQ option analysis, system-design
        component coverage) so NEW assessment types add richness WITHOUT a
        schema change.
      * ``tags`` for qualitative markers.

    IMPORTANT invariants:
      * EXPOSED, never applied — the Assessment Engine never mutates planner
        or learner metrics; consumers decide how to use this evidence.
      * IMMUTABLE — ``frozen=True`` so evidence cannot change after an
        assessment completes (a stable, auditable record).
    """
    model_config = ConfigDict(frozen=True, use_enum_values=True, extra="ignore")

    schema_version: str = EVIDENCE_SCHEMA_VERSION

    assessment_id: str
    user_id: str
    assessment_type: AssessmentType
    roadmap_node_id: Optional[str] = None
    mission_id: Optional[str] = None
    verdict: Optional[Verdict] = None

    # ---- canonical normalized scalars (type-agnostic) ----------------------
    accuracy: float = 0.0             # 0..1  — how correct the response was
    proficiency: float = 0.0          # 0..1  — overall demonstrated skill
    completion_quality: float = 0.0   # 0..1  — thoroughness / coverage
    confidence_delta: float = 0.0     # -1..1 — signed confidence suggestion
    difficulty_achieved: Optional[str] = None

    # ---- canonical boolean signals -----------------------------------------
    weakness_confirmation: bool = False
    revision_trigger: bool = False
    repeated_mistakes: bool = False

    # ---- extensibility (no schema change for future types) -----------------
    metrics: Dict[str, float] = Field(default_factory=dict)
    signals: Dict[str, bool] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)

    created_at: str = Field(default_factory=_now_iso)

    # ---- backward-compatible accessors (NOT serialized) --------------------
    # Keep the original Phase-3A field names working for any early consumer.
    @property
    def coding_accuracy(self) -> float:
        return self.accuracy

    @property
    def problem_solving(self) -> float:
        return self.proficiency

    @property
    def topic_confidence_delta(self) -> float:
        return self.confidence_delta


# Canonical alias — there is exactly ONE evidence model.
Evidence = AssessmentEvidence


class AssessmentRecommendation(BaseModel):
    next_action: str = "continue"     # continue | revise | advance | reattempt
    reason: str = ""
    suggested_difficulty: str = "maintain"


class Assessment(BaseModel):
    """The aggregate root persisted as one normalized ``assessments`` doc."""
    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    id: str = Field(default_factory=_uuid)
    user_id: str
    assessment_type: AssessmentType
    status: AssessmentStatus = AssessmentStatus.PENDING

    roadmap_node_id: Optional[str] = None
    mission_id: Optional[str] = None            # NULLABLE by design
    target_company: Optional[str] = None
    company_context: dict = Field(default_factory=dict)
    learner_context_snapshot: dict = Field(default_factory=dict)

    rubric: Optional[Rubric] = None
    question: Optional[Question] = None
    attempt: Optional[Attempt] = None
    result: Optional[Result] = None
    feedback: Optional[Feedback] = None
    evidence: Optional[Evidence] = None
    recommendation: Optional[AssessmentRecommendation] = None

    created_at: str = Field(default_factory=_now_iso)
    started_at: Optional[str] = None
    submitted_at: Optional[str] = None
    completed_at: Optional[str] = None
    time_taken_seconds: Optional[int] = None

    def to_doc(self) -> dict:
        """JSON-safe Mongo document (enum values coerced to str)."""
        return self.model_dump(mode="json")


class CreateAssessmentRequest(BaseModel):
    assessment_type: AssessmentType = AssessmentType.CODING
    roadmap_node_id: Optional[str] = None
    mission_id: Optional[str] = None
    target_company: Optional[str] = None
    difficulty: Optional[str] = None    # optional override: easy|medium|hard


class SubmitAssessmentRequest(BaseModel):
    passed_tests: int = 0
    total_tests: int = 0
    edge_cases_passed: int = 0
    edge_cases_total: int = 0
    claimed_time_complexity: Optional[str] = None
    time_taken_seconds: Optional[int] = None
    explanation: Optional[str] = None
    code: Optional[str] = None
    solved: Optional[bool] = None
