"""MissionContext — the single source of truth for "what am I learning now".

PHASE 3C.1 — Foundation Stabilization (Architecture Freeze), decision #1.

Every downstream subsystem (Coding Arena, Assessment Engine, AI Mentor,
Analytics, Practice) consumes THIS object and never independently infers the
topic, activity type, difficulty, learning stage, pattern, prerequisites or
representative problems. All of those come from the roadmap (the canonical
knowledge graph) plus live learner state — never from ad-hoc branching.

MissionContext is a plain, JSON-serialisable dataclass built purely from:
  * roadmap node metadata (the LearningNode abstraction), and
  * caller-supplied learner signals (target companies, revision context).

It performs NO scoring and NO problem I/O beyond reading the representative
pool ids for the node's pattern. It is pure and unit-testable (no DB/server).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Sequence

import problem_bank
import roadmap as roadmap_module
from services.problem_selection import representative_pool

# Coding-family activity types share the representative-problem pipeline.
_CODING_ACTIVITIES = {"coding"}


@dataclass
class MissionContext:
    """Canonical descriptor of today's (or a task's) learning objective."""

    node_id: str
    topic: Optional[str] = None            # human label of the node
    activity_type: Optional[str] = None    # study|coding|quiz|behavioral|design|system_design|flashcards
    assessment_type: Optional[str] = None  # quiz|coding|behavioral|design|system_design|none
    subject: Optional[str] = None          # track id
    domain: Optional[str] = None           # coding domain label / module label
    subdomain: Optional[str] = None        # module id
    difficulty: Optional[str] = None
    learning_stage: Optional[str] = None
    estimated_time: Optional[int] = None   # minutes
    coding_pattern: Optional[str] = None
    knowledge_base_node: Optional[str] = None
    representative_problem_ids: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    related_topics: List[str] = field(default_factory=list)
    learning_objectives: List[str] = field(default_factory=list)
    target_companies: List[str] = field(default_factory=list)
    revision_context: Optional[Dict[str, Any]] = None
    mission_id: Optional[str] = None

    # ---- derived conveniences (no branching on subject) ------------------ #
    @property
    def is_coding(self) -> bool:
        return self.activity_type in _CODING_ACTIVITIES

    @property
    def opens_arena(self) -> bool:
        """Coding objective -> Open Coding Arena (constraint #12)."""
        return self.is_coding

    @property
    def opens_knowledge_base(self) -> bool:
        """Non-coding objective -> Open Knowledge Base (constraint #12)."""
        return not self.is_coding

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_mission_context(
    node_id: str,
    *,
    roadmap: Optional[Any] = None,
    target_companies: Sequence[str] = (),
    revision_context: Optional[Dict[str, Any]] = None,
    mission_id: Optional[str] = None,
) -> Optional[MissionContext]:
    """Build a MissionContext from the roadmap node + learner signals.

    Returns ``None`` when the node id does not resolve. Reads activity_type /
    assessment_type straight off the node (they were stamped at build time);
    it never re-derives them.
    """
    r = roadmap or roadmap_module.get_roadmap()
    node = r.get(node_id)
    if not node:
        return None

    track = r.find_track(node_id)
    subject = (track or {}).get("id") or node.get("track")
    pattern = r.pattern_for_node(node_id)

    # Domain label: coding domain from the pattern map, else the module label.
    domain = None
    if pattern and pattern in problem_bank.PATTERN_TO_DOMAIN:
        domain = problem_bank.PATTERN_TO_DOMAIN[pattern][1]
    if not domain:
        module_id = node.get("module")
        module_node = r.get(module_id) if module_id else None
        domain = (module_node or {}).get("label") if module_node else None

    activity_type = node.get("activity_type")
    learning_stage = node.get("learning_stage")
    difficulty = node.get("difficulty")

    # Representative problem ids — only meaningful for coding objectives, and
    # scoped to this node's own pattern + stage (no future-topic leak).
    rep_ids: List[str] = []
    if activity_type in _CODING_ACTIVITIES and pattern:
        rep_ids = [
            p.get("id")
            for p in representative_pool(pattern, learning_stage=learning_stage)
        ]

    prerequisites = list(node.get("prerequisites", []) or [])
    for extra in (node.get("topic_prerequisites") or []):
        if extra not in prerequisites:
            prerequisites.append(extra)

    return MissionContext(
        node_id=node_id,
        topic=node.get("label"),
        activity_type=activity_type,
        assessment_type=node.get("assessment_type"),
        subject=subject,
        domain=domain,
        subdomain=node.get("module"),
        difficulty=difficulty,
        learning_stage=learning_stage,
        estimated_time=node.get("estimated_minutes"),
        coding_pattern=pattern,
        knowledge_base_node=node_id,
        representative_problem_ids=rep_ids,
        prerequisites=prerequisites,
        related_topics=list(node.get("related", []) or []),
        learning_objectives=list(node.get("learning_objectives", []) or []),
        target_companies=[c for c in (target_companies or [])],
        revision_context=revision_context,
        mission_id=mission_id,
    )
