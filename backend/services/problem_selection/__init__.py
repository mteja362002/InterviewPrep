"""Canonical problem selection service (Phase 3C.1 freeze).

ONE selector, reused by Mission Planner, Coding Arena, Assessment Engine,
AI Mentor and Practice More. No subsystem may re-implement problem filtering.

Data ownership (frozen):
  * Representative problems (curriculum / mission / arena / assessment) come
    ONLY from ``problem_bank``.
  * The Practice Library (``dev_seed.json`` via ``leetcode_catalog``) is used
    ONLY as assessment *overflow* when the representative pool is insufficient
    — never by the Mission Engine / Coding Arena.
"""
from .selector import (  # noqa: F401
    arena_problem_count,
    representative_pool,
    select_representative,
    select_one,
    split_arena_assessment,
    ProblemSelectionResult,
)
