"""Unlocked-node selection for the additive learning engine."""
from __future__ import annotations

from typing import Iterable, List, Optional

from roadmap import get_roadmap


def _completed_node_ids(progress_rows: Iterable[dict]) -> set:
    rows = list(progress_rows or [])
    completed = set()
    for row in rows:
        if isinstance(row, dict):
            status = (row.get("status") or "").lower()
            node_id = row.get("node_id")
            if node_id and status in {"completed", "mastered", "revision_due"}:
                completed.add(node_id)
    return completed


def get_unlocked_nodes(progress_rows: Optional[Iterable[dict]] = None) -> List[dict]:
    """Return roadmap learning nodes whose prerequisites are satisfied."""
    roadmap = get_roadmap()
    completed_ids = _completed_node_ids(progress_rows)
    return roadmap.get_unlocked_nodes(completed_ids)


def is_node_unlocked(node_id: str, progress_rows: Optional[Iterable[dict]] = None) -> bool:
    """Return whether the roadmap prerequisites for a node are already complete."""
    if isinstance(progress_rows, dict):
        completed = set(progress_rows)
    elif isinstance(progress_rows, (set, list, tuple)):
        if progress_rows and isinstance(next(iter(progress_rows)), str):
            completed = set(progress_rows)
        else:
            completed = _completed_node_ids(progress_rows)
    else:
        completed = _completed_node_ids(progress_rows)
    return get_roadmap().is_unlocked(node_id, completed)


def next_unlockable_nodes(progress_rows: Optional[Iterable[dict]] = None) -> List[dict]:
    """Return nodes that are now unlocked but not already completed."""
    completed_ids = _completed_node_ids(progress_rows)
    unlocked = get_unlocked_nodes(progress_rows)
    return [node for node in unlocked if node.get("id") not in completed_ids]


def first_unlockable_node(progress_rows: Optional[Iterable[dict]] = None) -> Optional[dict]:
    """Return the first roadmap learning node that is unlockable."""
    unlocked = next_unlockable_nodes(progress_rows)
    return unlocked[0] if unlocked else None


def get_curriculum_eligible_nodes(progress_rows: Optional[Iterable[dict]] = None) -> List[dict]:
    """Return learning nodes passing both subject-gate and node-gate.

    Unlike ``get_unlocked_nodes`` (which checks only node-level
    prerequisites), this also enforces ``subject_prerequisites`` — nodes
    from locked subjects (e.g. DSA before Java is completed) are
    filtered out.

    Used by the Curriculum Progression Engine's eligibility layer.
    """
    roadmap = get_roadmap()
    completed_ids = _completed_node_ids(progress_rows)
    return roadmap.get_curriculum_eligible_nodes(completed_ids)
