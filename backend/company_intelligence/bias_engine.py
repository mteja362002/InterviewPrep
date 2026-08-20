"""Company Weight Engine — adaptive bias.

Turns a company's planning-priority guidance into a BOUNDED, deterministic
multiplier applied to the Company Intelligence signal. Kept intentionally small
([0.85, 1.15]) so it nudges ordering without ever dominating learner signals.

Operates on a duck-typed CompanyContext (profiles exposing
``priority_hierarchy`` and ``company_id``). No I/O, no randomness.
"""
from __future__ import annotations

from typing import Any, Optional

_BIAS_MIN = 0.85
_BIAS_MAX = 1.15

# Map a priority-hierarchy LABEL (as authored in compiled `planner.priority`)
# to the subject key(s) it refers to. Fuzzy: matched as a lowercase substring.
_PRIORITY_LABEL_SUBJECTS = {
    "dsa": {"dsa"},
    "data structures": {"dsa"},
    "programming": {"programming_fundamentals"},
    "java": {"java"},
    "system design": {"high_level_design", "low_level_design"},
    "lld": {"low_level_design"},
    "low-level": {"low_level_design"},
    "hld": {"high_level_design"},
    "high-level": {"high_level_design"},
    "database": {"dbms"},
    "dbms": {"dbms"},
    "core cs": {"dbms", "operating_systems", "computer_networks"},
    "operating": {"operating_systems"},
    "network": {"computer_networks"},
}


def _subject_key(node: dict) -> Optional[str]:
    track = node.get("track") or node.get("id")
    if not track:
        return None
    return {"hld": "high_level_design", "lld": "low_level_design"}.get(track, track)


def _priority_multiplier_for_profile(profile: Any, subject_key: str) -> float:
    """Earlier position in the company's priority hierarchy -> higher nudge.

    Returns 1.0 (neutral) when the subject is not mentioned in the hierarchy.
    """
    hierarchy = profile.priority_hierarchy or []
    if not hierarchy:
        return 1.0
    n = len(hierarchy)
    for idx, label in enumerate(hierarchy):
        subjects = _PRIORITY_LABEL_SUBJECTS.get(str(label).strip().lower())
        if not subjects:
            # try substring match against known labels
            low = str(label).strip().lower()
            subjects = set()
            for key, subj in _PRIORITY_LABEL_SUBJECTS.items():
                if key in low:
                    subjects |= subj
        if subject_key in subjects:
            # position 0 -> top of hierarchy -> max nudge; last -> min nudge.
            frac = idx / max(n - 1, 1)
            return _BIAS_MAX - frac * (_BIAS_MAX - _BIAS_MIN)
    return 1.0


def company_bias_multiplier(company_context: Any, node: dict, *, level: str = "software_engineer") -> float:
    """Bounded mean priority-based multiplier across the selected companies."""
    subject_key = _subject_key(node)
    if not subject_key or company_context is None or getattr(company_context, "is_empty", True):
        return 1.0
    values = [_priority_multiplier_for_profile(p, subject_key) for p in company_context]
    if not values:
        return 1.0
    mean = sum(values) / len(values)
    return max(_BIAS_MIN, min(_BIAS_MAX, mean))
