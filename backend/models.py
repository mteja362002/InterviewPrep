"""Pydantic models for PrepOS."""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone
import uuid


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============ Auth ============

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=80)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    
class ResendVerificationRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
    
class MessageResponse(BaseModel):
    message: str
    email: str


class UserPublic(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: EmailStr
    name: str
    role: str = "user"
    avatar_url: Optional[str] = None
    onboarding_completed: bool = False
    created_at: str


# ============ Profile ============

class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=80)
    avatar_url: Optional[str] = None
    bio: Optional[str] = Field(default=None, max_length=280)
    headline: Optional[str] = Field(default=None, max_length=120)


# ============ Onboarding ============

class OnboardingSelfAssessment(BaseModel):
    programming_fundamentals: int = Field(ge=0, le=10, default=0)
    dsa: int = Field(ge=0, le=10, default=0)
    java: int = Field(ge=0, le=10, default=0)
    lld: int = Field(ge=0, le=10, default=0)
    hld: int = Field(ge=0, le=10, default=0)
    operating_systems: int = Field(ge=0, le=10, default=0)
    dbms: int = Field(ge=0, le=10, default=0)
    computer_networks: int = Field(ge=0, le=10, default=0)


class OnboardingPayload(BaseModel):
    target_companies: List[str] = Field(min_length=1, max_length=20)
    current_position: str  # Student | 0-1 | 1-3 | 3-5 | 5+
    daily_study_hours: float = Field(ge=1, le=8)
    self_assessment: OnboardingSelfAssessment
    interview_target_date: str  # ISO date string


class OnboardingRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    target_companies: List[str]
    current_position: str
    daily_study_hours: float
    self_assessment: OnboardingSelfAssessment
    interview_target_date: str
    estimated_prep_days: int
    created_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)


# ============ Settings ============

class AIConfig(BaseModel):
    provider: str = "gemini"  # gemini | openai | claude | deepseek
    model_name: str = "gemini-flash-latest"
    api_key: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0, le=2)


class NotificationPrefs(BaseModel):
    email_daily_digest: bool = True
    email_weekly_report: bool = True
    push_streak_reminders: bool = True
    push_upcoming_revisions: bool = True
    push_mission_updates: bool = True


class UserSettings(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    theme: str = "dark"  # dark | light | system
    ai_config: AIConfig = Field(default_factory=AIConfig)
    notification_prefs: NotificationPrefs = Field(default_factory=NotificationPrefs)
    updated_at: str = Field(default_factory=_now_iso)


class SettingsUpdate(BaseModel):
    theme: Optional[str] = None
    ai_config: Optional[AIConfig] = None
    notification_prefs: Optional[NotificationPrefs] = None


# ============ Missions ============

TOPIC_KEYS = ["dsa", "java", "lld", "hld", "operating_systems", "dbms", "computer_networks"]


class MissionTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    kind: str  # 'practice' | 'study' | 'revise'
    topic: str  # one of TOPIC_KEYS
    completed: bool = False
    completed_at: Optional[str] = None
    # Optional linkage for adaptive coding practice
    pattern: Optional[str] = None
    problem_count: Optional[int] = None
    # Canonical roadmap node id for Knowledge Base / AI Mentor linkage
    node_id: Optional[str] = None


class DailyMission(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    date: str  # YYYY-MM-DD (user local date, but stored as UTC date)
    title: str
    focus_area: str
    focus_topic: str  # one of TOPIC_KEYS
    difficulty: str  # easy | medium | hard
    estimated_duration_minutes: int
    learning_objective: str
    tasks: List[MissionTask]
    revision_task_ids: List[str] = []  # ids of tasks that are revision items
    status: str = "in_progress"  # in_progress | completed | skipped
    # Adaptive Mission Engine (Sprint · iter 13) — filled once per day by the
    # AI planner. Cached on the mission doc so refreshes never re-invoke the LLM.
    tomorrow_preview: Optional[dict] = None
    week_goal: Optional[dict] = None
    ai_narrative: Optional[str] = None  # 1-2 sentence "why this mission today" from the mentor
    # Phase 4B: the Learning Engine's explainable "why this node" object
    # (services/learning_engine/insight.py) — same source of truth read by
    # AI Mentor's context builder and reusable by future Analytics/Mobile.
    recommendation_insight: Optional[dict] = None
    created_at: str = Field(default_factory=_now_iso)
    completed_at: Optional[str] = None
    skipped_at: Optional[str] = None
    # Phase 3C · Mission → Assessment workflow (all OPTIONAL → old missions
    # and existing APIs stay byte-identical; populated only when the
    # assessment checkpoint is used). The mission ORCHESTRATES only; it never
    # evaluates assessments or computes learner updates.
    assessment_id: Optional[str] = None          # linked Assessment (Engine-owned)
    assessment_status: Optional[str] = None       # mirror of the assessment status
    assessment_available: bool = False            # study+coding done → checkpoint unlocked
    workflow_state: Optional[str] = None          # computed coarse workflow stage


class KnowledgeProgress(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    topic: str  # one of TOPIC_KEYS
    score: float = 0.0  # 0-100
    completions: int = 0
    last_updated: str = Field(default_factory=_now_iso)


class StudyStreak(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    current_streak: int = 0
    longest_streak: int = 0
    last_active_date: Optional[str] = None  # YYYY-MM-DD
    updated_at: str = Field(default_factory=_now_iso)


class RevisionItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    task_title: str
    topic: str
    stage: int = 0  # 0..4 (1d, 3d, 7d, 14d, 30d)
    next_review_date: str  # YYYY-MM-DD
    created_at: str = Field(default_factory=_now_iso)
    completed: bool = False


class ActivityEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    kind: str  # mission_completed | mission_skipped | task_completed | profile_updated | settings_changed | daily_login | mission_generated
    title: str
    description: Optional[str] = None
    ts: str = Field(default_factory=_now_iso)


class OnboardingPatch(BaseModel):
    target_companies: Optional[List[str]] = None
    current_position: Optional[str] = None
    daily_study_hours: Optional[float] = Field(default=None, ge=1, le=8)
    interview_target_date: Optional[str] = None


# ============ Problem Bank & Feedback ============

class ProblemAssignment(BaseModel):
    """A problem tied to a mission task or extra-practice slot."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    problem_id: str  # references PROBLEMS list in problem_bank.py
    mission_id: Optional[str] = None
    pattern: str
    source: str = "mission"  # 'mission' | 'practice_more'
    status: str = "assigned"  # assigned | solved | attempted | skipped
    notes: Optional[str] = None
    assigned_at: str = Field(default_factory=_now_iso)
    completed_at: Optional[str] = None


class ProblemFeedbackPayload(BaseModel):
    difficulty_rating: str  # easy | medium | hard
    solved_status: str  # without_hints | one_hint | multi_hints | could_not_solve
    confidence: int = Field(ge=1, le=10)
    time_taken_minutes: int = Field(ge=0, le=600)
    notes: Optional[str] = Field(default=None, max_length=1000)


class ProblemFeedback(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    problem_id: str
    assignment_id: Optional[str] = None
    mission_id: Optional[str] = None
    pattern: str
    difficulty_rating: str
    solved_status: str
    confidence: int
    time_taken_minutes: int
    notes: Optional[str] = None
    submitted_at: str = Field(default_factory=_now_iso)


class MissionAdjustment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    for_date: str  # YYYY-MM-DD (date this adjustment applies to)
    reason: str
    detected_weaknesses: List[str] = []
    inserted_prerequisites: List[str] = []
    advance: bool = False  # true if user is progressing
    # RC1.3.2A · additive audit trail for the composition/validation
    # decisions. Both are optional so historical rows keep validating.
    composition: Optional[dict] = None
    validation: Optional[dict] = None
    created_at: str = Field(default_factory=_now_iso)


class WeaknessRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    pattern: str
    signal: str  # low_confidence | many_hints | timeout | could_not_solve
    detected_at: str = Field(default_factory=_now_iso)
    resolved_at: Optional[str] = None


# ============ Roadmap Knowledge Graph ============

class KnowledgeNode(BaseModel):
    """Per-user per-node state on a versioned roadmap."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    roadmap_version: str = "v1"
    node_id: str
    status: str = "not_started"  # not_started | in_progress | completed | mastered | revision_due
    confidence: float = 0.0  # 0-10
    weakness_score: float = 0.0  # 0-100 (higher = weaker)
    revision_bucket: str = "green"  # green | yellow | red
    mastery_percentage: float = 0.0  # 0-100
    last_revision: Optional[str] = None
    next_revision: Optional[str] = None
    revision_stage: int = 0  # 0..5 spaced-repetition stage (see services/revision_engine.py)
    completion_date: Optional[str] = None
    attempts: int = 0
    actual_solve_minutes: int = 0
    bookmarked: bool = False
    favorite: bool = False
    notes: Optional[str] = None
    updated_at: str = Field(default_factory=_now_iso)


class RoadmapNodeProgress(BaseModel):
    """Per-user progress for one explicit learning node in the master roadmap."""
    user_id: str
    node_id: str
    track: str
    module: str
    topic: str
    subtopic: str
    status: str = Field(default="not_started", pattern="^(not_started|learning|completed|revision_due)$")
    mastery: float = Field(default=0.0, ge=0, le=100)
    confidence: float = Field(default=0.0, ge=0, le=10)
    weakness_score: float = Field(default=100.0, ge=0, le=100)
    times_practiced: int = Field(default=0, ge=0)
    times_completed: int = Field(default=0, ge=0)
    average_time: float = Field(default=0.0, ge=0)
    last_practiced: Optional[datetime] = None
    next_revision: Optional[datetime] = None
    revision_stage: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KnowledgeNoteUpdate(BaseModel):
    notes: str = Field(max_length=5000)


class KnowledgeConfidenceUpdate(BaseModel):
    confidence: float = Field(ge=0, le=10)


class KnowledgeStatusUpdate(BaseModel):
    status: str = Field(pattern="^(not_started|in_progress|completed|mastered|revision_due)$")


class KnowledgeAttemptUpdate(BaseModel):
    actual_minutes: Optional[int] = Field(default=None, ge=0, le=6000)


# ============ AI-generated knowledge content ============

class KnowledgeContent(BaseModel):
    """Cached AI-generated content for a single roadmap node.

    Cache key = (node_id, roadmap_version). Global (not per-user) — every
    learner sees the same generated content. That way the first user's cost
    benefits everyone; regenerate is opt-in.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str
    roadmap_version: str = "v1"
    provider: str = "gemini"
    model_name: str = "gemini-flash-latest"
    # The generated payload — one nested dict per Section.
    # Shape is validated by prompt_builder.parse_content().
    theory: Optional[dict] = None
    examples: Optional[List[dict]] = None
    interview_tips: Optional[List[str]] = None
    common_mistakes: Optional[List[dict]] = None
    flashcards: Optional[List[dict]] = None
    related_topics: Optional[List[dict]] = None
    prerequisites: Optional[List[dict]] = None
    generated_by: Optional[str] = None  # user_id of the first requester
    generated_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)
