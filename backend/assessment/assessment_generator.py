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
    nid = roadmap_node_id.lower()
    # Longest key first so 'two_pointers' wins over 'pointers' style partials.
    for pattern in sorted(problem_bank.PATTERN_TO_DOMAIN.keys(), key=len, reverse=True):
        if pattern in nid or pattern.replace("_", "") in nid.replace("_", ""):
            return pattern
    return None


def _candidate_pool(pattern: Optional[str]) -> List[dict]:
    if pattern:
        pool = problem_bank.problems_by_pattern(pattern)
        if pool:
            return pool
    return list(problem_bank.PROBLEMS)


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
) -> Optional[dict]:
    """Deterministically select ONE problem_bank problem for an assessment."""
    pattern = _resolve_pattern(roadmap_node_id)
    diff = clamp_difficulty(difficulty)
    pool = _candidate_pool(pattern)

    def _filter(items, *, by_company: bool):
        out = []
        for p in items:
            if p.get("difficulty") != diff:
                continue
            if by_company and target_company:
                if target_company.lower() not in [c.lower() for c in p.get("companies", [])]:
                    continue
            out.append(p)
        return out

    # Prefer company-matched at the target difficulty; then any at difficulty;
    # then any in the pool (difficulty unavailable for this pattern).
    for candidates in (
        _filter(pool, by_company=True),
        _filter(pool, by_company=False),
        pool,
    ):
        if candidates:
            return sorted(candidates, key=_rank_key)[0]
    return None


def generate_coding_assessment(
    *,
    roadmap_node_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    target_company: Optional[str] = None,
    **_ignored,
) -> Question:
    """Generate a coding Question by reference to problem_bank."""
    problem = select_problem(
        roadmap_node_id=roadmap_node_id,
        difficulty=difficulty,
        target_company=target_company,
    )
    if not problem:
        raise ValueError("No coding problem could be selected for the given context.")

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
