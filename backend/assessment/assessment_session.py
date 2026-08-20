"""Assessment Session — the lifecycle state machine.

Enforces valid transitions across the assessment lifecycle:

    pending -> started -> submitted -> evaluated -> completed

Deterministic, pure over the Assessment aggregate. Timestamps and
time-taken are stamped on transition. Invalid transitions raise
``InvalidTransition`` (surfaced by the API as 409).
"""
from __future__ import annotations

from datetime import datetime, timezone

from .schemas import Assessment, AssessmentStatus, Attempt


class InvalidTransition(Exception):
    """Raised on an illegal assessment status transition."""


_ALLOWED = {
    AssessmentStatus.PENDING.value: {AssessmentStatus.STARTED.value},
    AssessmentStatus.STARTED.value: {AssessmentStatus.SUBMITTED.value},
    AssessmentStatus.SUBMITTED.value: {AssessmentStatus.EVALUATED.value},
    AssessmentStatus.EVALUATED.value: {AssessmentStatus.COMPLETED.value},
    AssessmentStatus.COMPLETED.value: set(),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _status_value(a: Assessment) -> str:
    s = a.status
    return s.value if isinstance(s, AssessmentStatus) else str(s)


def can_transition(current: str, target: str) -> bool:
    return target in _ALLOWED.get(current, set())


def _require(a: Assessment, target: AssessmentStatus) -> None:
    current = _status_value(a)
    if not can_transition(current, target.value):
        raise InvalidTransition(f"Cannot move assessment from '{current}' to '{target.value}'.")


def start(a: Assessment) -> Assessment:
    _require(a, AssessmentStatus.STARTED)
    a.status = AssessmentStatus.STARTED.value
    a.started_at = _now()
    return a


def submit(a: Assessment, attempt: Attempt) -> Assessment:
    _require(a, AssessmentStatus.SUBMITTED)
    a.status = AssessmentStatus.SUBMITTED.value
    a.attempt = attempt
    a.submitted_at = attempt.submitted_at or _now()
    if a.started_at:
        try:
            delta = datetime.fromisoformat(a.submitted_at) - datetime.fromisoformat(a.started_at)
            a.time_taken_seconds = max(0, int(delta.total_seconds()))
        except Exception:
            a.time_taken_seconds = attempt.time_taken_seconds
    else:
        a.time_taken_seconds = attempt.time_taken_seconds
    return a


def mark_evaluated(a: Assessment) -> Assessment:
    _require(a, AssessmentStatus.EVALUATED)
    a.status = AssessmentStatus.EVALUATED.value
    return a


def complete(a: Assessment) -> Assessment:
    _require(a, AssessmentStatus.COMPLETED)
    a.status = AssessmentStatus.COMPLETED.value
    a.completed_at = _now()
    return a
