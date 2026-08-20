"""Evaluation Engine — deterministic, rubric-driven scoring.

No LLM, no inference. Each rubric dimension is scored 0..100 from the
structured attempt inputs; the weighted sum yields the overall score and a
verdict. Extension point: an AI-assisted evaluator can later populate the
same ``DimensionScore`` objects without changing consumers.
"""
from __future__ import annotations

from typing import List, Optional

from .schemas import (
    Attempt, DimensionScore, Question, Result, Rubric, Verdict,
)

_CORRECT_THRESHOLD = 90.0
_PARTIAL_THRESHOLD = 40.0
_MIN_EXPLANATION_CHARS = 80


def _ratio(num: int, den: int) -> float:
    if den <= 0:
        return 0.0
    return max(0.0, min(1.0, num / den))


def _normalize_complexity(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    return "".join(str(text).lower().split())


def _score_correctness(a: Attempt) -> float:
    if a.total_tests > 0:
        return round(_ratio(a.passed_tests, a.total_tests) * 100.0, 2)
    if a.solved is True:
        return 100.0
    if a.solved is False:
        return 0.0
    return 0.0


def _score_complexity(a: Attempt, q: Optional[Question]) -> (float, str):
    expected = _normalize_complexity(q.expected_time_complexity if q else None)
    claimed = _normalize_complexity(a.claimed_time_complexity)
    if not expected or not claimed:
        return 60.0, "unknown"          # neutral when we cannot compare
    if claimed == expected:
        return 100.0, "optimal"
    return 40.0, "suboptimal"


def _score_edge_cases(a: Attempt) -> (float, float):
    if a.edge_cases_total > 0:
        cov = _ratio(a.edge_cases_passed, a.edge_cases_total)
        return round(cov * 100.0, 2), cov
    # No edge cases declared: mirror correctness at a discount (neutral).
    return 60.0, 0.0


def _score_communication(a: Attempt) -> float:
    if not a.explanation:
        return 0.0
    length = len(a.explanation.strip())
    if length >= _MIN_EXPLANATION_CHARS:
        return 100.0
    return round(min(1.0, length / _MIN_EXPLANATION_CHARS) * 100.0, 2)


def _score_code_quality(a: Attempt) -> float:
    # Deterministic heuristic: any code submitted + solved earns quality;
    # otherwise neutral. Kept simple & explainable for Phase 3A.
    if a.code and a.code.strip():
        return 80.0 if (a.solved or a.passed_tests >= max(1, a.total_tests)) else 60.0
    return 50.0


def _verdict(score: float) -> Verdict:
    if score >= _CORRECT_THRESHOLD:
        return Verdict.CORRECT
    if score >= _PARTIAL_THRESHOLD:
        return Verdict.PARTIALLY_CORRECT
    return Verdict.INCORRECT


def evaluate(attempt: Attempt, rubric: Rubric, question: Optional[Question] = None) -> Result:
    """Score one attempt against its rubric. Deterministic."""
    complexity_score, complexity_rating = _score_complexity(attempt, question)
    edge_score, edge_cov = _score_edge_cases(attempt)
    raw = {
        "correctness": _score_correctness(attempt),
        "complexity": complexity_score,
        "edge_cases": edge_score,
        "communication": _score_communication(attempt),
        "code_quality": _score_code_quality(attempt),
    }

    dimension_scores: List[DimensionScore] = []
    overall = 0.0
    for dim in rubric.dimensions:
        s = float(raw.get(dim.key, 0.0))
        overall += s * dim.weight
        dimension_scores.append(DimensionScore(
            key=dim.key, label=dim.label, score=round(s, 2),
            weight=dim.weight, detail=dim.description,
        ))

    overall = round(overall, 2)
    return Result(
        verdict=_verdict(overall),
        overall_score=overall,
        dimension_scores=dimension_scores,
        complexity_rating=complexity_rating,
        edge_case_coverage=round(edge_cov, 3),
        completion_status="completed",
    )
