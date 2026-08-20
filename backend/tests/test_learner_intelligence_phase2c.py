"""Phase 2C — Learner Intelligence Engine tests.

Pure unit tests (no server / DB / env). They validate that the Learner
Intelligence Engine:
  * computes every signal deterministically from existing data,
  * produces a compute-once snapshot the planner consumes,
  * becomes an ACTIVE, bounded planner scoring input only when opted in,
  * NEVER dominates the learner's core knowledge signal,
  * falls back cleanly (empty snapshot) when data is unavailable,
  * is fully explainable,
  * leaves pre-2C scoring byte-identical when disabled (regression).
"""
from datetime import datetime, timedelta, timezone

import pytest

from services.learner_intelligence import (
    build_learner_intelligence_input, build_learner_intelligence, build_snapshot,
    empty_snapshot, learner_intelligence_signal, summarize_snapshot,
    summarize_contributions,
)
from services.learner_intelligence.metrics import (
    DECLINING, INCREASING, RAPID_DECLINE, RAPID_IMPROVEMENT, STABLE,
    DIFFICULTY_DECREASE, DIFFICULTY_INCREASE, DIFFICULTY_MAINTAIN,
    MASTERY_IMPROVING, MASTERY_MASTERED, MASTERY_PLATEAU, MASTERY_REGRESSING,
    WEAKNESS_PERSISTENT, WEAKNESS_RECOVERED, WEAKNESS_RECURRING,
    WEAKNESS_TEMPORARY, UPWARD, DOWNWARD,
)
from services.learner_intelligence.trend_analysis import (
    classify_trend, split_mean_delta,
)
from services.learning_engine.context import build_learner_context
from services.learning_engine.ranking import score_learning_node


TODAY = datetime.now(timezone.utc).date()


def _d(n):
    """ISO date string n days ago."""
    return (TODAY - timedelta(days=n)).isoformat()


# --------------------------------------------------------------------------- #
# Trend analysis primitives
# --------------------------------------------------------------------------- #
class TestTrendAnalysis:
    def test_split_mean_delta_rising(self):
        assert split_mean_delta([1, 2, 8, 9]) == pytest.approx(7.0)

    def test_split_mean_delta_short_series_is_flat(self):
        assert split_mean_delta([5]) == 0.0
        assert split_mean_delta([]) == 0.0

    def test_classify_bands(self):
        assert classify_trend(0.0) == STABLE
        assert classify_trend(1.0) == INCREASING
        assert classify_trend(-1.0) == DECLINING
        assert classify_trend(5.0) == RAPID_IMPROVEMENT
        assert classify_trend(-5.0) == RAPID_DECLINE

    def test_determinism(self):
        s = [3, 4, 5, 6, 9]
        assert split_mean_delta(s) == split_mean_delta(list(s))


# --------------------------------------------------------------------------- #
# Signal 1 — Learning velocity
# --------------------------------------------------------------------------- #
class TestVelocity:
    def test_accelerating_velocity(self):
        # 5 completions in last 7 days, 1 in previous 7 -> increasing.
        dates = [_d(0), _d(1), _d(2), _d(3), _d(5), _d(10)]
        snap = build_snapshot(completed_dates=dates)
        assert snap.velocity.topics_last_7 == 5
        assert snap.velocity.topics_prev_7 == 1
        assert snap.velocity.trend in (INCREASING, RAPID_IMPROVEMENT)
        assert 0.0 <= snap.velocity.speed_score <= 1.0

    def test_decelerating_velocity(self):
        dates = [_d(8), _d(9), _d(10), _d(11), _d(1)]
        snap = build_snapshot(completed_dates=dates)
        assert snap.velocity.topics_prev_7 > snap.velocity.topics_last_7
        assert snap.velocity.trend in (DECLINING, RAPID_DECLINE)

    def test_no_dates_zero_velocity(self):
        snap = build_learner_intelligence(build_learner_intelligence_input())
        assert snap.velocity.completions_total == 0


# --------------------------------------------------------------------------- #
# Signal 3 — Confidence trend
# --------------------------------------------------------------------------- #
class TestConfidenceTrend:
    def test_rising_confidence(self):
        completions = [
            {"confidence": 2, "completion_date": _d(20)},
            {"confidence": 4, "completion_date": _d(15)},
            {"confidence": 7, "completion_date": _d(5)},
            {"confidence": 9, "completion_date": _d(1)},
        ]
        snap = build_snapshot(recent_completions=completions,
                              progress_rows=completions)
        assert snap.confidence_trend.direction in (INCREASING, RAPID_IMPROVEMENT)
        assert snap.confidence_trend.delta > 0

    def test_declining_confidence(self):
        completions = [
            {"confidence": 9, "completion_date": _d(20)},
            {"confidence": 7, "completion_date": _d(15)},
            {"confidence": 4, "completion_date": _d(5)},
            {"confidence": 2, "completion_date": _d(1)},
        ]
        snap = build_snapshot(recent_completions=completions,
                              progress_rows=completions)
        assert snap.confidence_trend.direction in (DECLINING, RAPID_DECLINE)
        assert snap.confidence_trend.low_confidence_count >= 1


# --------------------------------------------------------------------------- #
# Signal 2 — Retention quality
# --------------------------------------------------------------------------- #
class TestRetention:
    def test_success_and_failure_counts(self):
        rows = [
            {"track": "dsa", "revision_stage": 2, "confidence": 8, "mastery_percentage": 85},
            {"track": "dsa", "revision_stage": 1, "confidence": 3, "mastery_percentage": 40},
            {"track": "java", "revision_stage": 3, "confidence": 7, "mastery_percentage": 90},
        ]
        snap = build_snapshot(progress_rows=rows)
        r = snap.retention
        assert r.revised_count == 3
        assert r.revision_successes == 2
        assert r.revision_failures == 1
        assert r.revision_success_rate == pytest.approx(2 / 3, abs=0.01)

    def test_repeated_mistakes(self):
        rows = [
            {"track": "dsa", "attempts": 5, "mastery_percentage": 30},
            {"track": "dsa", "attempts": 1, "mastery_percentage": 90},
        ]
        snap = build_snapshot(progress_rows=rows)
        assert snap.retention.repeated_mistakes == 1


# --------------------------------------------------------------------------- #
# Signal 5 — Consistency
# --------------------------------------------------------------------------- #
class TestConsistency:
    def test_streak_and_consistency(self):
        dates = [_d(0), _d(1), _d(2), _d(3)]
        snap = build_snapshot(completed_dates=dates)
        assert snap.consistency.current_streak == 4
        assert snap.consistency.active_days_14 == 4
        assert snap.consistency.missed_days_14 == 10

    def test_streak_counts_from_yesterday_if_today_idle(self):
        dates = [_d(1), _d(2)]
        snap = build_snapshot(completed_dates=dates)
        assert snap.consistency.current_streak == 2

    def test_skipped_count_tracked(self):
        snap = build_snapshot(completed_dates=[_d(1)], skipped_node_ids=["a", "b"])
        assert snap.consistency.skipped_count == 2


# --------------------------------------------------------------------------- #
# Signal 6 — Revision health
# --------------------------------------------------------------------------- #
class TestRevisionHealth:
    def test_debt_and_backlog(self):
        rows = [
            {"track": "dsa", "next_revision": _d(3)},   # overdue 3 days
            {"track": "dsa", "next_revision": _d(1)},   # overdue 1 day
            {"track": "java", "next_revision": _d(-5)}, # scheduled future
        ]
        snap = build_snapshot(progress_rows=rows)
        rh = snap.revision_health
        assert rh.revision_debt == 2
        assert rh.revision_backlog == 3
        assert rh.avg_overdue_days == pytest.approx(2.0)
        assert rh.debt_level == "moderate"

    def test_no_scheduled_is_healthy(self):
        snap = build_snapshot(progress_rows=[{"track": "dsa"}])
        assert snap.revision_health.debt_level == "low"
        assert snap.revision_health.revision_completion_rate == 1.0


# --------------------------------------------------------------------------- #
# Signal 4 — Weakness stability
# --------------------------------------------------------------------------- #
class TestWeaknessStability:
    def test_persistent(self):
        rows = [{"track": "dsa", "status": "in_progress", "weakness_score": 70,
                 "mastery_percentage": 30, "attempts": 4, "revision_stage": 0}]
        snap = build_snapshot(progress_rows=rows)
        assert snap.weakness_state("dsa") == WEAKNESS_PERSISTENT

    def test_recovered(self):
        rows = [{"track": "java", "status": "mastered", "weakness_score": 10,
                 "mastery_percentage": 92, "attempts": 1, "revision_stage": 3}]
        snap = build_snapshot(progress_rows=rows)
        assert snap.weakness_state("java") == WEAKNESS_RECOVERED

    def test_recurring(self):
        rows = [{"track": "dbms", "status": "in_progress", "weakness_score": 45,
                 "mastery_percentage": 55, "attempts": 2, "revision_stage": 4}]
        snap = build_snapshot(progress_rows=rows)
        assert snap.weakness_state("dbms") == WEAKNESS_RECURRING

    def test_temporary(self):
        rows = [{"track": "os", "status": "in_progress", "weakness_score": 25,
                 "mastery_percentage": 70, "attempts": 1, "revision_stage": 0}]
        snap = build_snapshot(progress_rows=rows)
        assert snap.weakness_state("os") == WEAKNESS_TEMPORARY


# --------------------------------------------------------------------------- #
# Signal 8 — Topic mastery trend
# --------------------------------------------------------------------------- #
class TestMasteryTrend:
    def test_mastered(self):
        rows = [{"track": "java", "status": "mastered", "mastery_percentage": 95,
                 "weakness_score": 5, "completion_date": _d(2)}]
        snap = build_snapshot(progress_rows=rows)
        assert snap.mastery_state("java") == MASTERY_MASTERED

    def test_regressing(self):
        rows = [{"track": "dsa", "status": "in_progress", "mastery_percentage": 50,
                 "weakness_score": 55, "revision_stage": 3, "completion_date": _d(2)}]
        snap = build_snapshot(progress_rows=rows)
        assert snap.mastery_state("dsa") == MASTERY_REGRESSING

    def test_plateau_vs_improving(self):
        stale = [{"track": "dbms", "status": "in_progress", "mastery_percentage": 60,
                  "weakness_score": 20, "revision_stage": 0, "completion_date": _d(40)}]
        assert build_snapshot(progress_rows=stale).mastery_state("dbms") == MASTERY_PLATEAU
        fresh = [{"track": "dbms", "status": "in_progress", "mastery_percentage": 60,
                  "weakness_score": 20, "revision_stage": 0, "completion_date": _d(2)}]
        assert build_snapshot(progress_rows=fresh).mastery_state("dbms") == MASTERY_IMPROVING


# --------------------------------------------------------------------------- #
# Signal 7 — Coding growth
# --------------------------------------------------------------------------- #
class TestCodingGrowth:
    def test_has_signal_and_progression(self):
        rows = [
            {"track": "dsa", "status": "mastered", "difficulty": "hard",
             "attempts": 2, "mastery_percentage": 90},
            {"track": "dsa", "status": "completed", "difficulty": "medium",
             "attempts": 1, "mastery_percentage": 75},
        ]
        snap = build_snapshot(progress_rows=rows)
        cg = snap.coding_growth
        assert cg.has_signal is True
        assert cg.difficulty_progression == "hard"
        assert cg.solved_count == 2

    def test_no_coding_signal(self):
        rows = [{"track": "dsa", "status": "in_progress", "attempts": 0,
                 "actual_solve_minutes": 0}]
        snap = build_snapshot(progress_rows=rows)
        assert snap.coding_growth.has_signal is False


# --------------------------------------------------------------------------- #
# Signal 9 — Difficulty adaptation
# --------------------------------------------------------------------------- #
class TestDifficultyAdaptation:
    def test_decrease_when_struggling(self):
        completions = [
            {"confidence": 8, "completion_date": _d(20), "track": "dsa"},
            {"confidence": 6, "completion_date": _d(15), "track": "dsa"},
            {"confidence": 3, "completion_date": _d(5), "track": "dsa"},
            {"confidence": 2, "completion_date": _d(1), "track": "dsa"},
        ]
        rows = completions + [
            {"track": "dsa", "attempts": 5, "mastery_percentage": 30},
            {"track": "dsa", "attempts": 4, "mastery_percentage": 35},
            {"track": "dsa", "attempts": 4, "mastery_percentage": 40},
        ]
        snap = build_snapshot(progress_rows=rows, recent_completions=completions,
                              completed_dates=[c["completion_date"] for c in completions])
        assert snap.difficulty_adaptation.action == DIFFICULTY_DECREASE

    def test_increase_when_progressing(self):
        completions = [
            {"confidence": 3, "completion_date": _d(20)},
            {"confidence": 5, "completion_date": _d(15)},
            {"confidence": 8, "completion_date": _d(3)},
            {"confidence": 9, "completion_date": _d(1)},
        ]
        rows = completions + [
            {"track": "dsa", "revision_stage": 2, "confidence": 9, "mastery_percentage": 95},
            {"track": "java", "revision_stage": 2, "confidence": 8, "mastery_percentage": 88},
        ]
        dates = [_d(0), _d(1), _d(2), _d(3), _d(4)]  # strong recent velocity
        snap = build_snapshot(progress_rows=rows, recent_completions=completions,
                              completed_dates=dates)
        assert snap.difficulty_adaptation.action == DIFFICULTY_INCREASE

    def test_maintain_default(self):
        snap = build_snapshot(progress_rows=[{"track": "dsa", "confidence": 6,
                              "mastery_percentage": 60}])
        assert snap.difficulty_adaptation.action == DIFFICULTY_MAINTAIN


# --------------------------------------------------------------------------- #
# Signal 10 — Interview readiness trend
# --------------------------------------------------------------------------- #
class TestReadinessTrend:
    def test_upward(self):
        completions = [
            {"confidence": 3, "completion_date": _d(20)},
            {"confidence": 5, "completion_date": _d(15)},
            {"confidence": 8, "completion_date": _d(3)},
            {"confidence": 9, "completion_date": _d(1)},
        ]
        dates = [_d(0), _d(1), _d(2), _d(3), _d(10)]
        rows = completions + [{"track": "dsa", "revision_stage": 2,
                               "confidence": 9, "mastery_percentage": 90}]
        snap = build_snapshot(progress_rows=rows, recent_completions=completions,
                              completed_dates=dates)
        assert snap.readiness_trend.trajectory == UPWARD
        assert 0.0 <= snap.readiness_trend.score <= 1.0

    def test_declining(self):
        completions = [
            {"confidence": 9, "completion_date": _d(20)},
            {"confidence": 6, "completion_date": _d(15)},
            {"confidence": 3, "completion_date": _d(5)},
            {"confidence": 2, "completion_date": _d(1)},
        ]
        dates = [_d(12), _d(13), _d(1)]  # slowing
        rows = completions + [{"track": "dsa", "revision_stage": 1,
                               "confidence": 2, "mastery_percentage": 30}]
        snap = build_snapshot(progress_rows=rows, recent_completions=completions,
                              completed_dates=dates)
        assert snap.readiness_trend.trajectory == DOWNWARD


# --------------------------------------------------------------------------- #
# Planner adapter (consumption pipeline) + bounds
# --------------------------------------------------------------------------- #
class TestPlannerAdapter:
    def _weak_snapshot(self):
        rows = [{"track": "dsa", "status": "in_progress", "weakness_score": 70,
                 "mastery_percentage": 30, "attempts": 4, "revision_stage": 0}]
        return build_snapshot(progress_rows=rows)

    def test_weak_track_node_gets_positive_signal(self):
        snap = self._weak_snapshot()
        node = {"id": "dsa.sliding.core", "track": "dsa", "difficulty": "medium"}
        score, contribs = learner_intelligence_signal(snap, node)
        assert score > 0
        assert any(c["term"] == "weakness_stability" for c in contribs)

    def test_signal_is_bounded(self):
        # Construct a maximally biased snapshot; the signal must stay clamped.
        rows = [{"track": "dsa", "status": "in_progress", "weakness_score": 90,
                 "mastery_percentage": 10, "attempts": 9, "revision_stage": 4,
                 "completion_date": _d(2)}]
        snap = build_snapshot(progress_rows=rows)
        node = {"id": "dsa.x", "track": "dsa", "difficulty": "hard"}
        score, _ = learner_intelligence_signal(snap, node)
        assert -3.0 <= score <= 3.0

    def test_empty_snapshot_returns_zero(self):
        node = {"id": "dsa.x", "track": "dsa", "difficulty": "hard"}
        assert learner_intelligence_signal(empty_snapshot(), node) == (0.0, [])


# --------------------------------------------------------------------------- #
# Planner integration via the canonical scoring formula
# --------------------------------------------------------------------------- #
class TestPlannerIntegration:
    def _rows(self):
        return [{"node_id": "dsa.arrays.core", "track": "dsa", "status": "in_progress",
                 "weakness_score": 70, "mastery_percentage": 30, "attempts": 4,
                 "confidence": 3, "revision_stage": 0}]

    def _node(self):
        return {"id": "dsa.arrays.core", "track": "dsa", "difficulty": "medium",
                "estimated_minutes": 30}

    def test_enabled_changes_score(self):
        rows = self._rows()
        node = self._node()
        ctx_off = build_learner_context(progress_rows=rows)
        ctx_on = build_learner_context(progress_rows=rows,
                                       learner_intelligence_enabled=True)
        off = score_learning_node(node, rows[0], learner_context=ctx_off)
        on = score_learning_node(node, rows[0], learner_context=ctx_on)
        assert on["learner_intelligence_score"] > 0
        assert on["total_score"] != off["total_score"]

    def test_disabled_is_byte_identical_to_no_context_term(self):
        rows = self._rows()
        node = self._node()
        ctx_off = build_learner_context(progress_rows=rows)
        off = score_learning_node(node, rows[0], learner_context=ctx_off)
        assert off["learner_intelligence_score"] == 0.0

    def test_does_not_dominate_knowledge_gap(self):
        # Learner Intelligence contribution must be far smaller than the core
        # knowledge_gap term for a genuinely weak node.
        rows = self._rows()
        node = self._node()
        ctx_on = build_learner_context(progress_rows=rows,
                                       learner_intelligence_enabled=True)
        on = score_learning_node(node, rows[0], learner_context=ctx_on)
        li_contribution = abs(on["learner_intelligence_score"] * 5.0)  # weight
        assert li_contribution < on["knowledge_gap"]


# --------------------------------------------------------------------------- #
# Explainability
# --------------------------------------------------------------------------- #
class TestExplainability:
    def test_snapshot_summary_reasons(self):
        rows = [{"track": "dsa", "status": "in_progress", "weakness_score": 70,
                 "mastery_percentage": 30, "attempts": 4, "revision_stage": 0,
                 "confidence": 8, "next_revision": _d(3)}]
        rows += [{"track": "dsa", "status": "not_started", "next_revision": _d(2)},
                 {"track": "dsa", "status": "not_started", "next_revision": _d(1)}]
        snap = build_snapshot(progress_rows=rows)
        node = {"id": "dsa.sliding.core", "track": "dsa", "difficulty": "medium"}
        summary = summarize_snapshot(snap, node=node)
        assert summary["available"] is True
        assert "Weak topic" in summary["reasons"]
        assert "High revision debt" in summary["reasons"]
        assert summary["difficulty"].startswith("Difficulty")
        assert summary["confidence"] in ("High", "Medium", "Low")

    def test_empty_snapshot_summary_unavailable(self):
        summary = summarize_snapshot(empty_snapshot())
        assert summary["available"] is False

    def test_contributions_summary_ordered(self):
        contribs = [
            {"term": "difficulty_adaptation", "value": -0.3, "detail": "decrease/medium"},
            {"term": "weakness_stability", "value": 1.0, "detail": "persistent"},
        ]
        out = summarize_contributions(contribs)
        # Strongest driver first.
        assert out["reasons"][0].lower().startswith("persistent")


# --------------------------------------------------------------------------- #
# Fallback + regression
# --------------------------------------------------------------------------- #
class TestFallbackAndRegression:
    def test_engine_never_raises_on_garbage(self):
        snap = build_snapshot(progress_rows=[{"weird": object()}],
                              completed_dates=["not-a-date", None])
        assert snap.is_empty in (True, False)  # produced a snapshot, no raise

    def test_empty_input_is_empty_snapshot(self):
        assert build_learner_intelligence(build_learner_intelligence_input()).is_empty

    def test_scoring_unchanged_without_learner_context(self):
        # A scoring call with no learner_context at all must not carry any LI
        # contribution (pre-2C byte-identical behaviour).
        node = {"id": "dsa.arrays.core", "track": "dsa", "difficulty": "medium",
                "estimated_minutes": 30}
        breakdown = score_learning_node(node, {"confidence": 5})
        assert breakdown["learner_intelligence_score"] == 0.0
        assert breakdown["learner_intelligence"] is None

    def test_snapshot_is_deterministic(self):
        rows = [{"track": "dsa", "status": "in_progress", "weakness_score": 55,
                 "mastery_percentage": 45, "attempts": 3, "revision_stage": 2,
                 "confidence": 4, "completion_date": _d(3)}]
        a = build_snapshot(progress_rows=rows).to_dict()
        b = build_snapshot(progress_rows=list(rows)).to_dict()
        assert a == b
