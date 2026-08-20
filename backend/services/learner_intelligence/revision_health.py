"""Signal 6 — Revision Health.

How heavy is the learner's spaced-repetition backlog? Read directly from the
``next_revision`` / ``revision_stage`` fields the Revision Engine already
writes onto ``knowledge_nodes`` rows — no parallel store.

Metrics emitted:
    * revision_debt — count of overdue revisions (next_revision <= today).
    * revision_backlog — count of all scheduled revisions.
    * avg_overdue_days — mean lateness across overdue items.
    * revision_completion_rate — 0..1, (backlog - debt) / backlog.
    * debt_level — low / moderate / high bucket for quick explainability.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .context import LearnerIntelligenceInput
from .metrics import clamp, mean, parse_date, today_utc

_HIGH_DEBT = 5
_MODERATE_DEBT = 2


@dataclass
class RevisionHealth:
    revision_debt: int = 0
    revision_backlog: int = 0
    avg_overdue_days: float = 0.0
    revision_completion_rate: float = 1.0
    debt_level: str = "low"

    def to_dict(self) -> dict:
        return asdict(self)


def _debt_level(debt: int) -> str:
    if debt >= _HIGH_DEBT:
        return "high"
    if debt >= _MODERATE_DEBT:
        return "moderate"
    return "low"


def compute_revision_health(inp: LearnerIntelligenceInput) -> RevisionHealth:
    """Compute revision-health metrics from scheduled revision state."""
    today = today_utc()
    scheduled = [
        r for r in (inp.progress_rows or [])
        if isinstance(r, dict) and r.get("next_revision")
    ]
    if not scheduled:
        return RevisionHealth()

    overdue_days = []
    for row in scheduled:
        d = parse_date(row.get("next_revision"))
        if d is not None and d <= today:
            overdue_days.append((today - d).days)

    debt = len(overdue_days)
    backlog = len(scheduled)
    avg_overdue = mean(overdue_days) if overdue_days else 0.0
    completion_rate = clamp((backlog - debt) / backlog, 0.0, 1.0) if backlog else 1.0

    return RevisionHealth(
        revision_debt=debt,
        revision_backlog=backlog,
        avg_overdue_days=round(avg_overdue, 2),
        revision_completion_rate=round(completion_rate, 3),
        debt_level=_debt_level(debt),
    )
