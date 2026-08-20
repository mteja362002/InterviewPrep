"""Canonical, deterministic problem selector.

PHASE 3C.1 — Foundation Stabilization (Architecture Freeze).

This is the single source of truth for "which coding problems power this
learning objective". It is a pure module (no DB, no server, no wall-clock,
no randomness) so it is fully unit-testable in isolation.

Selection signals (all deterministic):
  * topic (via the coding ``pattern``)
  * learning stage (foundation / core / advanced — never mixed)
  * difficulty
  * target companies (soft preference, never a hard veto)
  * exclusions (recently solved / already-in-arena / already-in-assessment)
  * representative priority, interview frequency, stable id

Explicit empty state: if no representative problem matches the bounded
criteria the selector returns an EMPTY list. It NEVER silently substitutes an
unrelated topic (no "Two Sum" / default-coding fallback — constraint #14).

Future-topic leakage is impossible because selection is scoped to a single
``pattern`` (the node's own topic) and a single learning stage; problems for
yet-to-be-unlocked patterns are never in the candidate pool (constraint #9).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence

import problem_bank

_FREQ_RANK = {"very_high": 3, "high": 2, "medium": 1, "low": 0}


def _rank_key(p: dict):
    """Deterministic ranking: representative first, then frequency, then id."""
    return (
        0 if p.get("representative") else 1,
        -_FREQ_RANK.get(p.get("frequency", "low"), 0),
        int(p.get("leetcode_id") or 0),
        str(p.get("id") or ""),
    )


def arena_problem_count(estimated_minutes: Optional[int]) -> int:
    """Adaptive coding workload from today's mission duration (constraint #11).

    45m -> 1, 90m -> 2, 135m -> 3, 180m -> 4, 225m+ -> 5 (capped).
    """
    if not estimated_minutes or estimated_minutes <= 0:
        return 1
    return max(1, min(5, int(estimated_minutes) // 45))


def representative_pool(
    pattern: Optional[str],
    *,
    learning_stage: Optional[str] = None,
    difficulty: Optional[str] = None,
    representative_only: bool = False,
) -> List[dict]:
    """Return the deterministically-ranked candidate pool for one topic.

    Scoped to a single ``pattern`` (topic) and, when provided, a single
    ``learning_stage`` — so stages are never mixed and future topics never
    leak. ``difficulty`` is a soft narrowing: if problems exist at the exact
    difficulty within the stage we use them, otherwise the stage pool stands.
    """
    if not pattern:
        return []
    pool = list(problem_bank.problems_by_pattern(pattern))
    if representative_only:
        pool = [p for p in pool if p.get("representative")]
    if learning_stage:
        # Never mix stages. If nothing matches, that's an explicit empty pool.
        pool = [p for p in pool if p.get("learning_stage") == learning_stage]
    if difficulty:
        exact = [p for p in pool if p.get("difficulty") == difficulty]
        if exact:
            pool = exact
    return sorted(pool, key=_rank_key)


def _company_partition(pool: List[dict], target_companies: Sequence[str]) -> List[dict]:
    """Stable reorder: problems asked by a target company first (soft signal)."""
    if not target_companies:
        return pool
    wanted = {c.lower() for c in target_companies if c and c.lower() != "others"}
    if not wanted:
        return pool
    matched, rest = [], []
    for p in pool:
        companies = {c.lower() for c in (p.get("companies") or [])}
        (matched if companies & wanted else rest).append(p)
    return matched + rest


def select_representative(
    *,
    pattern: Optional[str],
    learning_stage: Optional[str] = None,
    difficulty: Optional[str] = None,
    target_companies: Sequence[str] = (),
    exclude_ids: Iterable[str] = (),
    count: int = 1,
) -> List[dict]:
    """Select up to ``count`` representative problems (problem_bank only).

    Deterministic, stage-bounded, exclusion-aware. Returns [] when nothing
    matches — never an unrelated-topic fallback.
    """
    if count <= 0:
        return []
    excluded = set(exclude_ids or ())
    pool = representative_pool(
        pattern, learning_stage=learning_stage, difficulty=difficulty
    )
    pool = [p for p in pool if p.get("id") not in excluded]
    pool = _company_partition(pool, target_companies)
    return pool[:count]


def select_one(
    *,
    pattern: Optional[str],
    learning_stage: Optional[str] = None,
    difficulty: Optional[str] = None,
    target_companies: Sequence[str] = (),
    exclude_ids: Iterable[str] = (),
) -> Optional[dict]:
    """Deterministically select ONE representative problem, else None."""
    got = select_representative(
        pattern=pattern,
        learning_stage=learning_stage,
        difficulty=difficulty,
        target_companies=target_companies,
        exclude_ids=exclude_ids,
        count=1,
    )
    return got[0] if got else None


# --------------------------------------------------------------------------- #
# Practice Library overflow (assessment ONLY) — dev_seed.json via catalog.
# Never used for Arena / Mission Engine.
# --------------------------------------------------------------------------- #
def _default_overflow_provider(
    *, pattern: Optional[str], learning_stage: Optional[str],
    difficulty: Optional[str], exclude_ids: set, count: int,
) -> List[dict]:
    """Best-effort equivalent problems from the Practice Library (dev_seed).

    Matched by the pattern name against the catalog problem's topic tags,
    narrowed by difficulty when possible. Deterministic (sorted by id).
    Guarded: any failure yields [] (explicit empty, never a wrong topic).
    """
    if not pattern or count <= 0:
        return []
    try:
        from leetcode_catalog import repository as catalog
    except Exception:
        return []
    try:
        needle = pattern.replace("_", " ")
        hits = catalog.search(needle, limit=100) or []
    except Exception:
        return []
    out: List[dict] = []
    for p in sorted(hits, key=lambda x: int(getattr(x, "leetcode_id", 0) or 0)):
        pid = f"catalog-{getattr(p, 'leetcode_id', '')}"
        if pid in exclude_ids:
            continue
        pdiff = (getattr(p, "difficulty", "") or "").lower()
        if difficulty and pdiff and pdiff != difficulty:
            continue
        out.append({
            "id": pid,
            "leetcode_id": getattr(p, "leetcode_id", None),
            "title": getattr(p, "title", ""),
            "difficulty": pdiff or None,
            "pattern": pattern,
            "learning_stage": learning_stage,
            "source": "practice_library",
            "representative": False,
        })
        if len(out) >= count:
            break
    return out


@dataclass
class ProblemSelectionResult:
    """Disjoint Arena vs Assessment selection for one learning objective."""
    arena: List[dict] = field(default_factory=list)
    assessment: List[dict] = field(default_factory=list)
    used_overflow: bool = False

    @property
    def arena_ids(self) -> List[str]:
        return [p.get("id") for p in self.arena]

    @property
    def assessment_ids(self) -> List[str]:
        return [p.get("id") for p in self.assessment]


def split_arena_assessment(
    *,
    pattern: Optional[str],
    learning_stage: Optional[str] = None,
    difficulty: Optional[str] = None,
    target_companies: Sequence[str] = (),
    arena_count: int = 1,
    assessment_count: int = 1,
    exclude_ids: Iterable[str] = (),
    overflow_provider: Optional[Callable[..., List[dict]]] = None,
) -> ProblemSelectionResult:
    """Select disjoint Arena and Assessment problems for the SAME objective.

    Arena and Assessment validate the same learning objective but must NEVER
    present identical representative problems (constraint #7). Arena is drawn
    first (problem_bank only); Assessment excludes every arena id. If the
    representative pool cannot satisfy the assessment size, equivalent
    problems are pulled from the Practice Library (dev_seed) — still never
    duplicating arena.
    """
    base_exclude = set(exclude_ids or ())

    arena = select_representative(
        pattern=pattern, learning_stage=learning_stage, difficulty=difficulty,
        target_companies=target_companies, exclude_ids=base_exclude,
        count=arena_count,
    )
    arena_ids = {p.get("id") for p in arena}

    assessment = select_representative(
        pattern=pattern, learning_stage=learning_stage, difficulty=difficulty,
        target_companies=target_companies,
        exclude_ids=base_exclude | arena_ids, count=assessment_count,
    )
    used_overflow = False
    if len(assessment) < assessment_count:
        need = assessment_count - len(assessment)
        already = base_exclude | arena_ids | {p.get("id") for p in assessment}
        provider = overflow_provider or _default_overflow_provider
        overflow = provider(
            pattern=pattern, learning_stage=learning_stage,
            difficulty=difficulty, exclude_ids=already, count=need,
        ) or []
        # Hard guarantee: overflow can never duplicate arena problems.
        overflow = [p for p in overflow if p.get("id") not in arena_ids]
        if overflow:
            used_overflow = True
        assessment = assessment + overflow

    return ProblemSelectionResult(
        arena=arena, assessment=assessment, used_overflow=used_overflow
    )
