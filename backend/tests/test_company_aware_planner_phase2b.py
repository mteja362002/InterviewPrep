"""Phase 2B — Company-aware Adaptive Planner tests.

Pure unit tests (no server/DB/env). They verify that compiled Company
Intelligence becomes an ACTIVE, bounded, deterministic planner signal that:
  * influences scoring only when explicitly enabled (opt-in),
  * differs by company / subject importance,
  * respects experience level (juniors get suppressed advanced-design emphasis),
  * scales with evidence confidence,
  * NEVER dominates learner intelligence,
  * falls back cleanly when Company Intelligence is unavailable,
  * is fully explainable.
"""
from dataclasses import dataclass, field
from typing import List

import pytest

from company_intelligence.bias_engine import company_bias_multiplier
from company_intelligence.explainability import summarize_contributions
from company_intelligence.scoring import (
    compute_company_intelligence_signal,
    experience_level_from_position,
)
from services.learning_engine.company_context import build_company_context
from services.learning_engine.context import build_learner_context
from services.learning_engine.ranking import score_learning_node


# --------------------------------------------------------------------------- #
# Duck-typed fakes for isolated engine tests
# --------------------------------------------------------------------------- #
@dataclass
class FakeProfile:
    company_id: str
    subjects: dict
    confidence: str
    priority_hierarchy: list = field(default_factory=list)


@dataclass
class FakeContext:
    _profiles: List[FakeProfile]

    @property
    def is_empty(self):
        return not self._profiles

    def __iter__(self):
        return iter(self._profiles)


def _dsa_node():
    return {"id": "dsa.arrays.core", "track": "dsa", "difficulty": "medium"}


def _hld_node():
    return {"id": "hld.caching.core", "track": "hld", "difficulty": "hard"}


# --------------------------------------------------------------------------- #
# Experience-level mapping
# --------------------------------------------------------------------------- #
class TestExperienceLevel:
    def test_position_mapping(self):
        assert experience_level_from_position("student") == "new_grad"
        assert experience_level_from_position("0-1") == "new_grad"
        assert experience_level_from_position("1-3") == "software_engineer"
        assert experience_level_from_position("3-5") == "senior"
        assert experience_level_from_position("5+") == "staff"
        assert experience_level_from_position(None) == "software_engineer"
        assert experience_level_from_position("weird") == "software_engineer"


# --------------------------------------------------------------------------- #
# Scoring engine (real compiled data)
# --------------------------------------------------------------------------- #
class TestScoringEngine:
    def test_google_dsa_signal_positive(self):
        cc = build_company_context(["google"])
        signal, contribs = compute_company_intelligence_signal(cc, _dsa_node())
        assert signal > 0
        assert contribs and contribs[0]["company_id"] == "google"
        assert contribs[0]["subject"] == "dsa"

    def test_company_specific_differences(self):
        # DSA is Critical for Google; for Oracle it is lower priority -> Google
        # yields a stronger DSA signal.
        g, _ = compute_company_intelligence_signal(build_company_context(["google"]), _dsa_node())
        o, _ = compute_company_intelligence_signal(build_company_context(["oracle"]), _dsa_node())
        assert g >= o

    def test_multiple_companies_average(self):
        cc = build_company_context(["google", "adobe"])
        signal, contribs = compute_company_intelligence_signal(cc, _dsa_node())
        assert len(contribs) == 2
        assert signal > 0

    def test_experience_level_suppresses_design_for_new_grad(self):
        cc = build_company_context(["google"])
        junior, _ = compute_company_intelligence_signal(cc, _hld_node(), level="new_grad")
        senior, _ = compute_company_intelligence_signal(cc, _hld_node(), level="senior")
        assert junior < senior  # never push advanced HLD as hard onto a new grad

    def test_confidence_scales_signal(self):
        high = FakeContext([FakeProfile("x", {"dsa": "Critical"}, "High")])
        low = FakeContext([FakeProfile("y", {"dsa": "Critical"}, "Low")])
        s_high, _ = compute_company_intelligence_signal(high, _dsa_node())
        s_low, _ = compute_company_intelligence_signal(low, _dsa_node())
        assert s_high > s_low  # uncertain evidence contributes less

    def test_empty_context_zero(self):
        cc = build_company_context([])
        signal, contribs = compute_company_intelligence_signal(cc, _dsa_node())
        assert signal == 0.0 and contribs == []

    def test_unknown_subject_neutral_not_crash(self):
        cc = build_company_context(["google"])
        signal, _ = compute_company_intelligence_signal(cc, {"id": "x", "track": "astrophysics"})
        assert signal >= 0.0  # neutral importance, no crash

    def test_deterministic(self):
        cc = build_company_context(["google", "adobe"])
        a, _ = compute_company_intelligence_signal(cc, _dsa_node(), level="senior")
        b, _ = compute_company_intelligence_signal(cc, _dsa_node(), level="senior")
        assert a == b


# --------------------------------------------------------------------------- #
# Bias engine
# --------------------------------------------------------------------------- #
class TestBiasEngine:
    def test_bias_bounded(self):
        cc = build_company_context(["google"])
        for node in (_dsa_node(), _hld_node()):
            m = company_bias_multiplier(cc, node)
            assert 0.85 <= m <= 1.15

    def test_empty_context_neutral(self):
        assert company_bias_multiplier(build_company_context([]), _dsa_node()) == 1.0


# --------------------------------------------------------------------------- #
# Explainability
# --------------------------------------------------------------------------- #
class TestExplainability:
    def test_summary_shape(self):
        _, contribs = compute_company_intelligence_signal(build_company_context(["google"]), _dsa_node())
        summary = summarize_contributions(contribs)
        assert summary["top_company"] == "google"
        assert summary["reasons"]
        assert summary["confidence"]

    def test_lowest_confidence_exposed(self):
        contribs = [
            {"company_id": "a", "subject": "dsa", "importance": "Critical", "confidence": "High", "contribution": 0.9},
            {"company_id": "b", "subject": "dsa", "importance": "Critical", "confidence": "Low", "contribution": 0.5},
        ]
        assert summarize_contributions(contribs)["confidence"] == "Low"


# --------------------------------------------------------------------------- #
# Planner integration (score_learning_node with LearnerContext)
# --------------------------------------------------------------------------- #
class TestPlannerIntegration:
    def _score(self, *, enabled, companies=("google",)):
        lc = build_learner_context(
            target_companies=list(companies),
            company_intelligence_enabled=enabled,
        )
        return score_learning_node(_dsa_node(), {}, target_companies=list(companies), learner_context=lc)

    def test_ci_adds_positive_term_when_enabled(self):
        off = self._score(enabled=False)
        on = self._score(enabled=True)
        assert off["company_intelligence_score"] == 0.0
        assert off["company_intelligence"] is None
        assert on["company_intelligence_score"] > 0.0
        assert on["company_intelligence"] is not None
        assert on["total_score"] > off["total_score"]

    def test_ci_never_dominates_learner_signal(self):
        # The CI contribution to total must be modest vs the learner knowledge
        # gap term (which for a fresh/weak learner is ~tens of points).
        on = self._score(enabled=True)
        ci_contribution = on["company_intelligence_score"] * 6.0  # weight
        assert ci_contribution <= 10.0
        assert on["knowledge_gap"] > ci_contribution  # learner signal dominates

    def test_explainability_present_in_breakdown(self):
        on = self._score(enabled=True)
        ci = on["company_intelligence"]
        assert ci["top_company"] == "google"
        assert any("Google" in r for r in ci["reasons"])
        assert ci["confidence"]


# --------------------------------------------------------------------------- #
# Fallback / backward compatibility
# --------------------------------------------------------------------------- #
class TestFallback:
    def test_enabled_but_unknown_company_falls_back(self):
        # 'others' is UI-only -> no compiled profile -> empty company_context.
        lc = build_learner_context(target_companies=["others"], company_intelligence_enabled=True)
        b = score_learning_node(_dsa_node(), {}, target_companies=["others"], learner_context=lc)
        assert b["company_intelligence_score"] == 0.0
        assert b["company_intelligence"] is None

    def test_disabled_adds_no_ci_term(self):
        # The ONLY difference between enabled and disabled must be the bounded
        # CI term (weight 6.0). Everything else (incl. Phase 4 adaptive terms
        # from the shared learner_context) is identical.
        on = score_learning_node(
            _dsa_node(), {}, target_companies=["google"],
            learner_context=build_learner_context(
                target_companies=["google"], company_intelligence_enabled=True),
        )
        off = score_learning_node(
            _dsa_node(), {}, target_companies=["google"],
            learner_context=build_learner_context(
                target_companies=["google"], company_intelligence_enabled=False),
        )
        assert off["company_intelligence_score"] == 0.0
        assert off["company_intelligence"] is None
        assert off["total_score"] == pytest.approx(on["total_score"] - on["company_intelligence_score"] * 6.0)

    def test_no_target_companies_no_ci(self):
        lc = build_learner_context(target_companies=[], company_intelligence_enabled=True)
        b = score_learning_node(_dsa_node(), {}, learner_context=lc)
        assert b["company_intelligence_score"] == 0.0
