"""Assessment → Learner Intelligence integration layer (Phase 3B).

The SINGLE, isolated, reusable bridge that makes Learner Intelligence the
canonical consumer of assessment evidence:

    Assessment -> AssessmentEvidence -> [this layer] -> LearnerIntelligenceUpdate

Guarantees:
    * DETERMINISTIC — no AI, no randomness, same evidence -> same update.
    * TYPE-AGNOSTIC — translates using ONLY the canonical evidence contract
      fields (accuracy / proficiency / confidence_delta / signals / metrics).
      There is NO `if assessment_type == ...` branching, so Coding, MCQ,
      Behavioral, LLD, HLD, Resume, Debugging, SQL, OS, Networking, and any
      future type flow through unchanged.
    * ISOLATED — depends only on the evidence CONTRACT (dict or
      AssessmentEvidence). The Assessment Engine never imports this; the app
      wires evidence into it at the orchestration boundary.

Dependency direction is one-way: Learner Intelligence consumes assessment
evidence; assessment code never consumes Learner Intelligence.
"""
from __future__ import annotations

from typing import Any, Optional

from .learner_update import LearnerIntelligenceUpdate


class InvalidEvidence(ValueError):
    """Raised when evidence cannot be validated for processing."""


# Deterministic, transparent scaling constants.
_MASTERY_SCALE = 20.0        # proficiency in [0,1] -> mastery delta in [-10, +10] pts
_GAP_SCALE = 15.0            # knowledge-gap adjustment magnitude
_STRENGTH_ACCURACY = 0.9     # accuracy threshold for a confirmed strength


def _get(evidence: Any, name: str, default=None):
    """Read a field from either an AssessmentEvidence object or a plain dict."""
    if evidence is None:
        return default
    if isinstance(evidence, dict):
        return evidence.get(name, default)
    return getattr(evidence, name, default)


def _verdict_str(evidence: Any) -> Optional[str]:
    v = _get(evidence, "verdict")
    return v.value if hasattr(v, "value") else v


def validate_evidence(evidence: Any) -> None:
    """Validate the minimal canonical contract. Raises ``InvalidEvidence``."""
    if evidence is None:
        raise InvalidEvidence("evidence is None")
    for required in ("assessment_id", "user_id"):
        if not _get(evidence, required):
            raise InvalidEvidence(f"evidence missing required field: {required}")


def _build_reasons(*, verdict, accuracy, proficiency, confidence_delta,
                   weakness, strength, revision_hint, mastery_delta,
                   difficulty) -> list:
    """Deterministic, human-readable explainability for the learner update."""
    pct = round(accuracy * 100)
    reasons = []
    if confidence_delta > 0:
        reasons.append(f"Confidence increased because the assessment verdict was '{verdict}' (accuracy {pct}%).")
    elif confidence_delta < 0:
        reasons.append(f"Confidence decreased because the assessment verdict was '{verdict}' (accuracy {pct}%).")
    else:
        reasons.append(f"Confidence unchanged (verdict '{verdict}', accuracy {pct}%).")
    if mastery_delta > 0:
        reasons.append(f"Mastery improved because demonstrated proficiency was {round(proficiency * 100)}%.")
    elif mastery_delta < 0:
        reasons.append(f"Mastery regressed because demonstrated proficiency was {round(proficiency * 100)}%.")
    if weakness:
        reasons.append(f"Weakness detected because accuracy ({pct}%) confirmed a gap on this topic.")
    if strength:
        reasons.append(f"Strength detected because of high accuracy ({pct}%) on a '{difficulty}' assessment.")
    if revision_hint:
        reasons.append("Revision suggested because the evidence indicates unstable retention.")
    return reasons


def process_evidence(evidence: Any, *, user_id: Optional[str] = None) -> LearnerIntelligenceUpdate:
    """Translate immutable evidence into a deterministic learner update."""
    validate_evidence(evidence)

    accuracy = float(_get(evidence, "accuracy", 0.0) or 0.0)
    proficiency = float(_get(evidence, "proficiency", 0.0) or 0.0)
    completion_quality = float(_get(evidence, "completion_quality", 0.0) or 0.0)
    confidence_delta = float(_get(evidence, "confidence_delta", 0.0) or 0.0)
    verdict = _verdict_str(evidence)
    weakness = bool(_get(evidence, "weakness_confirmation", False))
    revision_hint = bool(_get(evidence, "revision_trigger", False))
    repeated_mistakes = bool(_get(evidence, "repeated_mistakes", False))
    difficulty = _get(evidence, "difficulty_achieved")

    strength = (verdict == "correct") and accuracy >= _STRENGTH_ACCURACY
    mastery_delta = round((proficiency - 0.5) * _MASTERY_SCALE, 2)

    if weakness:
        knowledge_gap_adjustment = round((1.0 - accuracy) * _GAP_SCALE, 2)
    elif strength:
        knowledge_gap_adjustment = round(-1.0 * accuracy * _GAP_SCALE, 2)
    else:
        knowledge_gap_adjustment = 0.0

    learning_signals = {
        "accuracy": accuracy,
        "proficiency": proficiency,
        "completion_quality": completion_quality,
        "confidence_delta": confidence_delta,
        "verdict": verdict,
        "difficulty_achieved": difficulty,
        "repeated_mistakes": repeated_mistakes,
        "metrics": dict(_get(evidence, "metrics", {}) or {}),
    }

    reasons = _build_reasons(
        verdict=verdict, accuracy=accuracy, proficiency=proficiency,
        confidence_delta=confidence_delta, weakness=weakness, strength=strength,
        revision_hint=revision_hint, mastery_delta=mastery_delta, difficulty=difficulty,
    )

    return LearnerIntelligenceUpdate(
        user_id=user_id or _get(evidence, "user_id"),
        assessment_id=_get(evidence, "assessment_id"),
        assessment_type=_get(evidence, "assessment_type"),
        roadmap_node_id=_get(evidence, "roadmap_node_id"),
        confidence_delta=confidence_delta,
        mastery_delta=mastery_delta,
        weakness_detected=weakness,
        strength_detected=strength,
        knowledge_gap_adjustment=knowledge_gap_adjustment,
        revision_hint=revision_hint,
        learning_signals=learning_signals,
        reasons=reasons,
        evidence_schema_version=_get(evidence, "schema_version"),
    )


async def ingest_evidence(
    evidence: Any,
    *,
    user_id: Optional[str] = None,
    repo: Optional[Any] = None,
) -> LearnerIntelligenceUpdate:
    """Process evidence and append the resulting update to history.

    ``repo`` is injectable (DIP) for testing; defaults to the append-only
    Mongo repository. Deterministic translation happens before any I/O.
    """
    update = process_evidence(evidence, user_id=user_id)
    if repo is None:
        from .update_repository import default_repository
        repo = default_repository()
    await repo.append(update)
    return update
