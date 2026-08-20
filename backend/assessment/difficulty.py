"""Difficulty helpers for the Assessment Engine (deterministic).

Maps learner experience bands to a default assessment difficulty and offers a
pure next-difficulty recommendation from a verdict. NEVER reorders the
roadmap; this only chooses which problem tier an assessment targets.
"""
from __future__ import annotations

from typing import Optional

from .schemas import Verdict

_ORDER = ["easy", "medium", "hard"]

# Experience band -> starting difficulty (opaque tags; unknown -> medium).
_LEVEL_DIFFICULTY = {
    "student": "easy",
    "0-1": "easy",
    "1-3": "medium",
    "3-5": "medium",
    "5+": "hard",
}


def level_from_position(position: Optional[str]) -> str:
    """Return a normalized learner level tag from onboarding position."""
    return (position or "").strip().lower() or "unknown"


def default_difficulty(position: Optional[str]) -> str:
    return _LEVEL_DIFFICULTY.get(level_from_position(position), "medium")


def clamp_difficulty(difficulty: Optional[str]) -> str:
    d = (difficulty or "").strip().lower()
    return d if d in _ORDER else "medium"


def step(difficulty: str, direction: str) -> str:
    """Return the difficulty one step in ``direction`` (increase|decrease)."""
    d = clamp_difficulty(difficulty)
    idx = _ORDER.index(d)
    if direction == "increase":
        idx = min(idx + 1, len(_ORDER) - 1)
    elif direction == "decrease":
        idx = max(idx - 1, 0)
    return _ORDER[idx]


def recommend_from_verdict(difficulty: str, verdict: Verdict) -> str:
    """Deterministic difficulty recommendation after an evaluation."""
    if verdict == Verdict.CORRECT:
        return "increase"
    if verdict == Verdict.INCORRECT:
        return "decrease"
    return "maintain"
