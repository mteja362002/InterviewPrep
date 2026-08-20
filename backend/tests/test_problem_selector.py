"""Phase 3C.1 — canonical ProblemSelector service.

Pure unit tests (no server / DB). Cover: determinism, explicit empty state,
stage matching, adaptive volume, Arena/Assessment disjointness, and Practice
Library overflow that never duplicates Arena problems.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.problem_selection import (  # noqa: E402
    arena_problem_count, representative_pool, select_representative, select_one,
    split_arena_assessment,
)


def test_deterministic():
    a = select_representative(pattern="arrays", count=3)
    b = select_representative(pattern="arrays", count=3)
    assert [p["id"] for p in a] == [p["id"] for p in b]


def test_unknown_pattern_is_empty_not_fallback():
    assert select_representative(pattern="totally_unknown", count=3) == []
    assert select_representative(pattern=None, count=3) == []
    assert select_one(pattern=None) is None


def test_stage_is_never_mixed():
    pool = representative_pool("arrays", learning_stage="foundation")
    assert pool, "expected some foundation arrays problems"
    assert all(p.get("learning_stage") == "foundation" for p in pool)


def test_adaptive_volume():
    assert arena_problem_count(45) == 1
    assert arena_problem_count(90) == 2
    assert arena_problem_count(135) == 3
    assert arena_problem_count(180) == 4
    assert arena_problem_count(300) == 5   # capped
    assert arena_problem_count(None) == 1


def test_arena_and_assessment_are_disjoint():
    res = split_arena_assessment(pattern="arrays", arena_count=2, assessment_count=2)
    assert res.arena_ids and res.assessment_ids
    assert not (set(res.arena_ids) & set(res.assessment_ids))


def test_exclusions_are_respected():
    first = select_representative(pattern="arrays", count=1)
    fid = first[0]["id"]
    nxt = select_representative(pattern="arrays", exclude_ids=[fid], count=1)
    assert nxt and nxt[0]["id"] != fid


def test_assessment_overflow_uses_practice_library_without_duplicating_arena():
    # Force the representative pool to be insufficient for the assessment by
    # asking for more problems than exist, and inject a fake Practice Library
    # provider. Overflow must never duplicate an arena problem.
    captured = {}

    def fake_provider(*, pattern, learning_stage, difficulty, exclude_ids, count):
        captured["exclude_ids"] = set(exclude_ids)
        # Return a mix: one that collides with arena (must be filtered out) and
        # two clean practice-library problems.
        arena_collision = next(iter(exclude_ids)) if exclude_ids else "x"
        return [
            {"id": arena_collision, "source": "practice_library"},
            {"id": "catalog-9001", "source": "practice_library"},
            {"id": "catalog-9002", "source": "practice_library"},
        ]

    res = split_arena_assessment(
        pattern="arrays", arena_count=2, assessment_count=99,
        overflow_provider=fake_provider,
    )
    assert res.used_overflow is True
    # No overlap between arena and assessment.
    assert not (set(res.arena_ids) & set(res.assessment_ids))
    # The injected arena-colliding id must have been filtered from overflow.
    for aid in res.arena_ids:
        assert aid not in res.assessment_ids
    assert "catalog-9001" in res.assessment_ids


def test_arena_never_pulls_from_practice_library():
    # Arena selection must be representative-only (problem_bank); the overflow
    # provider is never consulted for the arena portion.
    called = {"n": 0}

    def provider(**kw):
        called["n"] += 1
        return []

    split_arena_assessment(
        pattern="arrays", arena_count=2, assessment_count=2,
        overflow_provider=provider,
    )
    # Representative pool for arrays is large enough for both -> no overflow.
    assert called["n"] == 0
