"""Read boundary for certified evidence and immutable, unverified legacy values.

Top-level historical scores are never certified by inference. New writers own
only ``certified_progress`` and its per-field source stamps. Planner compatibility
is an explicit view, not an actual-progress aggregation.
"""
from copy import deepcopy

ACTUAL = "certified_actual"
LEGACY = "unverified_legacy"
BASELINE = "onboarding_baseline"
FIELDS = frozenset({
    "mastery_percentage", "confidence", "weakness_score", "status",
    "revision_bucket", "completion_date", "attempts", "actual_solve_minutes",
    "last_revision", "next_revision", "revision_stage",
})
SOURCES = frozenset({"task_completion", "problem_feedback", "confidence_update",
                     "status_update", "attempt", "revision"})


def certified_fields(row):
    """Only fields stamped by a supported forward writer cross this boundary."""
    row = row or {}
    actual = row.get("certified_progress") or {}
    sources = actual.get("field_sources") or {}
    return {key: deepcopy(value) for key, value in actual.items()
            if key in FIELDS and sources.get(key, {}).get("source") in SOURCES
            and sources[key].get("recorded_at")}


def legacy_fields(row):
    # Do not use dates, scores, attempts, or status to guess their origin.
    if (row or {}).get("planner_progress_source") == BASELINE:
        return {}  # explicit runtime projection, never a historical database row
    return {key: deepcopy(value) for key, value in (row or {}).items() if key in FIELDS}


def actual_row(row, roadmap=None):
    row = row or {}
    result = {key: row[key] for key in ("node_id", "user_id", "roadmap_version",
                                      "notes", "bookmarked", "favorite") if key in row}
    result["evidence_classification"] = ACTUAL
    # Track identity is resolved with the pinned curriculum, never string guessing.
    if roadmap is not None and row.get("roadmap_version") == getattr(roadmap, "version", None):
        node = roadmap.get(row.get("node_id"))
        if node:
            result.update(certified_fields(row))
            if not result.get("status") and result.get("attempts", 0) > 0:
                # Attributable attempts establish activity, never mastery/completion.
                result["status"] = "in_progress"
            result["track"] = node.get("track") or node.get("id")
    return result


def planner_row(row):
    """Preserve historical planning inputs explicitly; actual fields take priority.

    A track derived for legacy display MUST NOT enter the evidence-weight formula.
    The context computes that formula from actual_row exclusively.
    """
    return {**row, **certified_fields(row),
            "planner_progress_source": ACTUAL if certified_fields(row) else row.get("planner_progress_source", LEGACY)}


def historical_facts(row):
    """Inspectable retained facts; their presence does not certify mastery."""
    return {key: row[key] for key in ("completion_date", "attempts", "actual_solve_minutes",
                                     "last_revision", "next_revision", "revision_stage")
            if key in row}
