"""Assessment Generator — builds an assessment question from context.

Coding assessments REUSE existing ``problem_bank`` metadata (by reference,
never duplicating problem definitions). Selection is fully deterministic:
given the same (node, company, level, difficulty) inputs the same problem is
chosen every time.

Selection pipeline:
    1. Resolve a coding PATTERN from the roadmap node id/label when possible.
    2. Build the candidate pool (pattern problems, else difficulty pool).
    3. Filter by difficulty and (optionally) target company.
    4. Deterministically rank and pick one.
"""
from __future__ import annotations

from typing import List, Optional

import problem_bank
from services.problem_selection import select_one as _select_one
from .difficulty import clamp_difficulty
from .schemas import AssessmentType, Question
from .assessment_types import register_generator

_FREQ_RANK = {"very_high": 3, "high": 2, "medium": 1, "low": 0}
# A conventional optimal complexity hint per pattern (guidance only).
_EXPECTED_COMPLEXITY = {
    "sliding_window": "O(n)", "two_pointers": "O(n)", "arrays": "O(n)",
    "hashing": "O(n)", "binary_search": "O(log n)", "stack": "O(n)",
    "linked_list": "O(n)", "trees": "O(n)", "graphs": "O(V+E)",
    "heap": "O(n log k)", "dynamic_programming": "O(n)", "greedy": "O(n log n)",
}


def _resolve_pattern(roadmap_node_id: Optional[str]) -> Optional[str]:
    """Best-effort deterministic pattern resolution from a node id."""
    if not roadmap_node_id:
        return None
    import roadmap as roadmap_module
    return roadmap_module.pattern_for_node(roadmap_node_id)


def _candidate_pool(pattern: Optional[str]) -> List[dict]:
    # Scoped to the topic's own pattern only. NO unrelated-topic fallback
    # (Phase 3C.1 freeze, constraint #14): an unresolved pattern yields an
    # empty pool, not the entire problem bank.
    if pattern:
        return problem_bank.problems_by_pattern(pattern)
    return []


def _rank_key(p: dict):
    # Deterministic: representative first, then frequency, then stable id.
    return (
        0 if p.get("representative") else 1,
        -_FREQ_RANK.get(p.get("frequency", "low"), 0),
        int(p.get("leetcode_id") or 0),
    )


def select_problem(
    *,
    roadmap_node_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    target_company: Optional[str] = None,
    learning_stage: Optional[str] = None,
    exclude_ids: Optional[List[str]] = None,
) -> Optional[dict]:
    """Deterministically select ONE problem_bank problem for an assessment.

    Delegates to the canonical problem selector (the SAME selector used by the
    Mission Planner, Coding Arena and AI Mentor) so no duplicate filtering
    logic exists. Returns ``None`` (explicit empty state) when the node's
    pattern cannot be resolved or the topic has no matching problem \u2014 it never
    substitutes an unrelated topic.
    """
    pattern = _resolve_pattern(roadmap_node_id)
    diff = clamp_difficulty(difficulty)
    companies = [target_company] if target_company else []
    return _select_one(
        pattern=pattern,
        learning_stage=learning_stage,
        difficulty=diff,
        target_companies=companies,
        exclude_ids=exclude_ids or (),
    )


def generate_coding_assessment(
    *,
    roadmap_node_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    target_company: Optional[str] = None,
    exclude_ids: Optional[List[str]] = None,
    **_ignored,
) -> Question:
    """Generate a coding Question by reference to problem_bank."""
    problem = select_problem(
        roadmap_node_id=roadmap_node_id,
        difficulty=difficulty,
        target_company=target_company,
        exclude_ids=exclude_ids,
    )
    if not problem:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="No coding problem could be selected for the given context. It may be exhausted or invalid."
        )

    pattern = problem.get("primary_pattern", problem.get("pattern"))
    return Question(
        prompt=f"Solve: {problem['title']}",
        problem_id=problem.get("id"),
        leetcode_id=problem.get("leetcode_id"),
        title=problem.get("title"),
        difficulty=problem.get("difficulty"),
        pattern=pattern,
        estimated_minutes=problem.get("estimated_minutes"),
        external_url=problem.get("leetcode_url"),
        expected_time_complexity=_EXPECTED_COMPLEXITY.get(pattern),
        metadata={
            "frequency": problem.get("frequency"),
            "tags": problem.get("tags", []),
            "prerequisite_patterns": problem.get("prerequisite_patterns", []),
            "learning_stage": problem.get("learning_stage"),
            "companies": problem.get("companies", []),
        },
    )


# Register the only implemented generator for Phase 3A.
register_generator(AssessmentType.CODING, generate_coding_assessment)
