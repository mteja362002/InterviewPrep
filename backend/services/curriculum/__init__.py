"""Curriculum metadata helpers (build-time only).

This package hosts the SINGLE canonical, build-time derivation of curriculum
metadata (``activity_type`` / ``assessment_type``) that is written *into* the
roadmap JSON. At RUNTIME nothing in the app derives these values — every
downstream subsystem simply reads the field off the roadmap node.

See ``activity_metadata`` for the frozen rules.
"""
from .activity_metadata import (  # noqa: F401
    ACTIVITY_TYPES,
    ASSESSMENT_TYPES,
    TRACK_ACTIVITY_TYPE,
    ACTIVITY_TO_ASSESSMENT,
    TRACK_ASSESSMENT_OVERRIDE,
    derive_activity_type,
    derive_assessment_type,
    stamp_node,
)
