"""Company Weight Engine — scoring.

Computes a single, bounded, DETERMINISTIC Company Intelligence signal for a
candidate node from compiled company artifacts (via a CompanyContext). This is
the numeric core that the Adaptive Planner adds as ONE extra weighted term.

Hard guarantees:
  * Deterministic. No randomness, no LLM, no I/O here (operates on the passed
    CompanyContext, which is already loaded from compiled JSON).
  * Bounded. The returned signal is small by construction so Company
    Intelligence can INFLUENCE but never DOMINATE learner intelligence.
  * Safe. Never raises for malformed/partial data — unknown labels fall back to
    neutral values.

This module reads a duck-typed CompanyContext (see
services.learning_engine.company_context): an iterable of profiles each exposing
``subjects`` (dict), ``confidence`` (str), ``priority_hierarchy`` (list) and
``company_id``. It does NOT import that module (keeps the Phase-1 layer free of a
dependency on the learning engine).
"""
from __future__ import annotations

from typing import Any, List, Optional, Tuple

from company_intelligence.bias_engine import company_bias_multiplier

# ---------------------------------------------------------------------------
# Deterministic label -> scalar maps. No company ids, no learner ids.
# ---------------------------------------------------------------------------
IMPORTANCE_SCALE = {
    "critical": 1.0,
    "very high": 0.85,
    "high": 0.7,
    "medium-high": 0.6,
    "medium": 0.5,
    "low-medium": 0.4,
    "low": 0.3,
    "very low": 0.15,
}
NEUTRAL_IMPORTANCE = 0.5

CONFIDENCE_SCALE = {
    "high": 1.0,
    "medium-high": 0.9,
    "medium": 0.8,
    "medium-low": 0.75,
    "low-medium": 0.7,
    "low": 0.6,
}
NEUTRAL_CONFIDENCE = 0.8

# Roadmap track id -> compiled-artifact subject key. Curriculum-structural
# aliasing only (NOT company-specific).
SUBJECT_ALIASES = {
    "hld": "high_level_design",
    "lld": "low_level_design",
}

# Canonical experience levels. Onboarding position -> level.
_POSITION_TO_LEVEL = {
    "student": "new_grad",
    "0-1": "new_grad",
    "1-3": "software_engineer",
    "3-5": "senior",
    "5+": "staff",
}
DEFAULT_LEVEL = "software_engineer"

# Level factor for DESIGN-family subjects (HLD/LLD). Suppresses advanced design
# emphasis for juniors so Company Intelligence never pushes advanced HLD onto a
# beginner ("Never use Staff signals for New Graduate"). Non-design subjects use
# a flat 1.0.
_DESIGN_SUBJECTS = {"high_level_design", "low_level_design"}
_DESIGN_LEVEL_FACTOR = {
    "new_grad": 0.6,
    "software_engineer": 0.85,
    "senior": 1.1,
    "staff": 1.2,
}


def experience_level_from_position(position: Optional[str]) -> str:
    """Map an onboarding position to a canonical experience level."""
    return _POSITION_TO_LEVEL.get((position or "").strip().lower(), DEFAULT_LEVEL)


def _importance_value(label: Optional[str]) -> float:
    if not label:
        return NEUTRAL_IMPORTANCE
    return IMPORTANCE_SCALE.get(str(label).strip().lower(), NEUTRAL_IMPORTANCE)


def _confidence_value(label: Optional[str]) -> float:
    if not label:
        return NEUTRAL_CONFIDENCE
    return CONFIDENCE_SCALE.get(str(label).strip().lower(), NEUTRAL_CONFIDENCE)


def _subject_key(node: dict) -> Optional[str]:
    track = node.get("track") or node.get("id")
    if not track:
        return None
    return SUBJECT_ALIASES.get(track, track)


def _level_factor(subject_key: str, level: str) -> float:
    if subject_key in _DESIGN_SUBJECTS:
        return _DESIGN_LEVEL_FACTOR.get(level, 0.85)
    return 1.0


def compute_company_intelligence_signal(
    company_context: Any,
    node: dict,
    *,
    level: str = DEFAULT_LEVEL,
) -> Tuple[float, List[dict]]:
    """Return ``(signal, contributions)`` for one candidate node.

    ``signal`` is the bounded Company Intelligence scalar (roughly 0..1.3):
        signal = mean_over_companies(importance * confidence * level_factor)
                 * company_bias_multiplier

    ``contributions`` is the per-company audit trail used by explainability.
    Empty context -> (0.0, []) so the planner cleanly falls back to the
    roadmap-only company signal.
    """
    if company_context is None or getattr(company_context, "is_empty", True):
        return 0.0, []

    subject_key = _subject_key(node)
    if not subject_key:
        return 0.0, []

    lvl_factor = _level_factor(subject_key, level)
    contributions: List[dict] = []
    total = 0.0

    for profile in company_context:
        importance_label = (profile.subjects or {}).get(subject_key)
        importance = _importance_value(importance_label)
        confidence_label = profile.confidence
        confidence = _confidence_value(confidence_label)
        contribution = importance * confidence * lvl_factor
        total += contribution
        contributions.append({
            "company_id": profile.company_id,
            "subject": subject_key,
            "importance": importance_label,
            "importance_value": round(importance, 3),
            "confidence": confidence_label,
            "confidence_value": round(confidence, 3),
            "level": level,
            "level_factor": lvl_factor,
            "contribution": round(contribution, 3),
        })

    if not contributions:
        return 0.0, []

    mean_contribution = total / len(contributions)
    bias = company_bias_multiplier(company_context, node, level=level)
    signal = mean_contribution * bias
    return round(signal, 4), contributions
