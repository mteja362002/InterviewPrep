"""Canonical, BUILD-TIME derivation of curriculum activity metadata.

PHASE 3C.1 — Foundation Stabilization (Architecture Freeze).

Constraint #3 of the freeze: *every roadmap node explicitly declares its
activity type*; no runtime module may infer it. To satisfy that, this module
is the ONE place the rules live, and it is invoked ONLY at build time:

    * ``scripts/generate_roadmap.py`` (future roadmap generation), and
    * ``scripts/migrate_activity_types.py`` (one-time migration of the
      existing ``data/roadmap_v1.json``).

Both stamp ``activity_type`` and ``assessment_type`` onto every node. At
runtime, ``MissionContext`` and every engine read those fields directly.

The rules are deterministic and keyed on the *curriculum subject* (track).
This subject keying is legitimate CURRICULUM AUTHORING done at build time —
it is NOT the forbidden runtime ``if subject == DSA`` branching, which the
freeze prohibits inside engines (Assessment, Arena, Planner, Mentor...).

Adding a brand-new subject therefore requires only one row here plus roadmap
content — no engine code changes.
"""
from __future__ import annotations

from typing import Dict, Tuple

# --------------------------------------------------------------------------- #
# Frozen enums
# --------------------------------------------------------------------------- #
ACTIVITY_TYPES: Tuple[str, ...] = (
    "study",
    "coding",
    "quiz",
    "behavioral",
    "design",
    "system_design",
    "flashcards",
)

ASSESSMENT_TYPES: Tuple[str, ...] = (
    "quiz",
    "coding",
    "behavioral",
    "design",
    "system_design",
    "none",
)

# --------------------------------------------------------------------------- #
# Subject (track) -> primary activity type. Build-time curriculum authoring.
# --------------------------------------------------------------------------- #
TRACK_ACTIVITY_TYPE: Dict[str, str] = {
    "dsa": "coding",
    "lld": "design",
    "hld": "system_design",
    "behavioral": "behavioral",
    "programming_fundamentals": "study",
    "java": "study",
    "operating_systems": "study",
    "dbms": "study",
    "computer_networks": "study",
    "projects": "study",
    "resume": "study",
}

# activity_type -> assessment_type (constraint #6 of the freeze).
ACTIVITY_TO_ASSESSMENT: Dict[str, str] = {
    "study": "quiz",
    "coding": "coding",
    "quiz": "quiz",
    "behavioral": "behavioral",
    "design": "design",
    "system_design": "system_design",
    "flashcards": "quiz",
}

# Subjects whose completion is not validated by an auto-generated assessment.
TRACK_ASSESSMENT_OVERRIDE: Dict[str, str] = {
    "resume": "none",
    "projects": "none",
}

_DEFAULT_ACTIVITY = "study"


def derive_activity_type(node: dict, track_id: str) -> str:
    """Return the activity_type for ``node`` (build-time).

    Precedence (idempotent + authorable):
      1. An explicit valid ``activity_type`` already on the node wins.
      2. A ``flashcards`` tag promotes the node to flashcards.
      3. Otherwise the subject's default from ``TRACK_ACTIVITY_TYPE``.
    """
    existing = node.get("activity_type")
    if existing in ACTIVITY_TYPES:
        return existing
    tags = [str(t).lower() for t in (node.get("tags") or [])]
    if "flashcards" in tags:
        return "flashcards"
    return TRACK_ACTIVITY_TYPE.get(track_id, _DEFAULT_ACTIVITY)


def derive_assessment_type(node: dict, track_id: str, activity_type: str) -> str:
    """Return the assessment_type for ``node`` (build-time)."""
    existing = node.get("assessment_type")
    if existing in ASSESSMENT_TYPES:
        return existing
    if track_id in TRACK_ASSESSMENT_OVERRIDE:
        return TRACK_ASSESSMENT_OVERRIDE[track_id]
    return ACTIVITY_TO_ASSESSMENT.get(activity_type, "quiz")


def stamp_node(node: dict, track_id: str) -> dict:
    """Idempotently write ``activity_type`` + ``assessment_type`` onto ``node``.

    Mutates and returns the node. Running twice is a no-op.
    """
    activity = derive_activity_type(node, track_id)
    node["activity_type"] = activity
    node["assessment_type"] = derive_assessment_type(node, track_id, activity)
    return node
