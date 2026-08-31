"""Shared primitives for the Learner Intelligence Engine (Phase 2C).

Everything in this module is a PURE, deterministic helper: safe coercions,
date parsing, a small statistics helper, and the canonical vocabulary of
trend / trajectory / state labels every signal module emits.

Design contract:
    * NO randomness, NO ML, NO I/O, NO Mongo. Pure functions only.
    * Labels are plain string constants so downstream consumers
      (planner_adapter, explainability, analytics, AI Mentor) can switch
      on a stable vocabulary without importing enums.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import List, Optional, Sequence

# --------------------------------------------------------------------------- #
# Canonical vocabulary
# --------------------------------------------------------------------------- #

# A learner-completed roadmap node counts toward activity when its status is
# one of these — canonical definition lives in services.progress_engine.
from services.progress_engine import COMPLETED_STATUSES  # re-exported for LI consumers

# Trend labels (confidence / velocity / retention / consistency).
INCREASING = "increasing"
STABLE = "stable"
DECLINING = "declining"
RAPID_IMPROVEMENT = "rapid_improvement"
RAPID_DECLINE = "rapid_decline"

# Trajectory labels (interview-readiness trend).
UPWARD = "upward"
DOWNWARD = "declining"
# (STABLE is reused for the flat trajectory.)

# Weakness-stability states.
WEAKNESS_TEMPORARY = "temporary"
WEAKNESS_PERSISTENT = "persistent"
WEAKNESS_RECOVERED = "recovered"
WEAKNESS_RECURRING = "recurring"

# Topic-mastery-trend states.
MASTERY_LEARNING = "learning"
MASTERY_IMPROVING = "improving"
MASTERY_PLATEAU = "plateau"
MASTERY_REGRESSING = "regressing"
MASTERY_MASTERED = "mastered"

# Difficulty-adaptation actions.
DIFFICULTY_MAINTAIN = "maintain"
DIFFICULTY_INCREASE = "increase"
DIFFICULTY_DECREASE = "decrease"

# The set of trend labels that read as "getting better".
POSITIVE_TRENDS = {INCREASING, RAPID_IMPROVEMENT, UPWARD}
# The set of trend labels that read as "getting worse".
NEGATIVE_TRENDS = {DECLINING, RAPID_DECLINE, DOWNWARD}


# --------------------------------------------------------------------------- #
# Safe coercions
# --------------------------------------------------------------------------- #

def safe_float(value, default: float = 0.0) -> float:
    """Coerce ``value`` to float, returning ``default`` on any failure."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default: int = 0) -> int:
    """Coerce ``value`` to int, returning ``default`` on any failure."""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def clamp(value: float, low: float, high: float) -> float:
    """Clamp ``value`` into the inclusive [low, high] band."""
    return max(low, min(high, value))


def mean(values: Sequence[float], default: float = 0.0) -> float:
    """Arithmetic mean of the non-None values (deterministic)."""
    vals = [v for v in values if v is not None]
    if not vals:
        return default
    return sum(vals) / len(vals)


# --------------------------------------------------------------------------- #
# Date helpers
# --------------------------------------------------------------------------- #

def parse_date(value) -> Optional[date]:
    """Parse an ISO date / datetime string (or date/datetime) to a ``date``.

    Accepts ``YYYY-MM-DD``, full ISO timestamps, and trailing ``Z``. Returns
    None for anything unparseable — never raises.
    """
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except Exception:
        pass
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def today_utc() -> date:
    """Current UTC calendar date. The ONLY time source in the engine so
    computations remain reproducible for a fixed 'now'."""
    return datetime.now(timezone.utc).date()


def days_ago(d: Optional[date], *, ref: Optional[date] = None) -> Optional[int]:
    """Whole days between ``d`` and ``ref`` (default today). None-safe."""
    if d is None:
        return None
    ref = ref or today_utc()
    return (ref - d).days
