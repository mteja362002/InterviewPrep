"""Learner State overlay — deterministic aggregation of evidence updates.

Given the append-only history of ``LearnerIntelligenceUpdate`` records, build
the learner-state view derived from assessment evidence. This is the
'Updated Learner State' the Phase 3B flow produces:

    Assessment -> Evidence -> Learner Intelligence -> Learner State

Pure and deterministic (sorted outputs, stable rounding). It is exposed for
future consumers (Analytics, AI Mentor, Company Readiness, and a future
planner-facing adapter). It is NOT wired into the planner's current snapshot,
so existing planner behavior remains identical (backward compatible).
"""
from __future__ import annotations

from typing import Dict, List

from .learner_update import LearnerIntelligenceUpdate

_GLOBAL = "_global"


def _empty_node() -> dict:
    return {
        "confidence_delta": 0.0,
        "mastery_delta": 0.0,
        "knowledge_gap_adjustment": 0.0,
        "assessment_count": 0,
        "weakness_detected": False,
        "strength_detected": False,
        "revision_hint": False,
        "reasons": [],
    }


def build_learner_state(updates: List[LearnerIntelligenceUpdate]) -> dict:
    """Aggregate updates (chronological) into a per-node learner-state view."""
    by_node: Dict[str, dict] = {}
    weaknesses, strengths, revision_nodes = set(), set(), set()

    ordered = sorted(updates, key=lambda u: u.created_at)
    for u in ordered:
        node = u.roadmap_node_id or _GLOBAL
        acc = by_node.setdefault(node, _empty_node())
        acc["confidence_delta"] = round(acc["confidence_delta"] + u.confidence_delta, 3)
        acc["mastery_delta"] = round(acc["mastery_delta"] + u.mastery_delta, 2)
        acc["knowledge_gap_adjustment"] = round(acc["knowledge_gap_adjustment"] + u.knowledge_gap_adjustment, 2)
        acc["assessment_count"] += 1
        acc["reasons"].extend(u.reasons)
        if u.weakness_detected:
            acc["weakness_detected"] = True
            weaknesses.add(node)
        if u.strength_detected:
            acc["strength_detected"] = True
            strengths.add(node)
        if u.revision_hint:
            acc["revision_hint"] = True
            revision_nodes.add(node)

    return {
        "by_node": by_node,
        "weaknesses": sorted(weaknesses),
        "strengths": sorted(strengths),
        "revision_nodes": sorted(revision_nodes),
        "assessment_count": len(ordered),
    }
