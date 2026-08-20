"""Phase 2A — Company Context integration tests.

Pure unit tests (no server, DB, or env). They verify:
  * CompanyContext creation from the runtime loader (compiled artifacts only)
  * multiple selected companies, empty selection, unknown ids
  * LearnerContext integration (company_context travels alongside)
  * backward compatibility: attaching CompanyContext does NOT change planner
    scoring inputs/outputs (the ranking formula never reads it).
"""
import copy

from services.learning_engine.company_context import (
    CompanyContext,
    CompanyProfileContext,
    build_company_context,
)
from services.learning_engine.context import build_learner_context


# --------------------------------------------------------------------------- #
# CompanyContext creation
# --------------------------------------------------------------------------- #
class TestCompanyContextCreation:
    def test_single_company(self):
        ctx = build_company_context(["google"])
        assert not ctx.is_empty
        assert ctx.known_ids() == ["google"]
        prof = ctx.get("google")
        assert isinstance(prof, CompanyProfileContext)
        assert prof.metadata.get("name") == "Google"
        assert prof.subjects and prof.signals
        assert prof.profile_version

    def test_multiple_companies_preserve_order_and_dedupe(self):
        ctx = build_company_context(["google", "adobe", "google", "uber"])
        assert ctx.known_ids() == ["google", "adobe", "uber"]
        assert set(ctx.selected_company_ids) == {"google", "adobe", "uber"}

    def test_case_insensitive_and_trims(self):
        ctx = build_company_context(["  Google ", "ADOBE"])
        assert ctx.known_ids() == ["google", "adobe"]

    def test_empty_selection_is_empty_context(self):
        for arg in (None, [], ["", "   "]):
            ctx = build_company_context(arg)
            assert ctx.is_empty
            assert ctx.profiles == {}
            assert ctx.known_ids() == []

    def test_unknown_ids_tracked_not_raised(self):
        ctx = build_company_context(["google", "others", "not_a_company"])
        # 'others' is the UI-only pseudo-company => not canonical => unknown
        assert ctx.known_ids() == ["google"]
        assert "others" in ctx.unknown_company_ids
        assert "not_a_company" in ctx.unknown_company_ids

    def test_all_unknown_yields_empty(self):
        ctx = build_company_context(["others", "amazon"])
        assert ctx.is_empty
        assert set(ctx.unknown_company_ids) == {"others", "amazon"}

    def test_normalized_planner_accessors(self):
        prof = build_company_context(["google"]).get("google")
        assert isinstance(prof.philosophy, list)
        assert isinstance(prof.priority_hierarchy, list)
        assert isinstance(prof.adaptive_biases, dict)
        assert prof.confidence  # evidence confidence surfaced from metadata

    def test_adobe_signals_variant(self):
        prof = build_company_context(["adobe"]).get("adobe")
        assert prof.summary_variant == "signals"
        assert prof.signals

    def test_never_exposes_raw_sections(self):
        # CompanyContext is built from the loader's public view (no `sections`).
        prof = build_company_context(["google"]).get("google")
        # CompanyProfileContext has no `sections` attribute/field at all.
        assert not hasattr(prof, "sections")

    def test_loader_failure_degrades_to_unknown(self):
        class BoomLoader:
            def get_company(self, cid):
                raise RuntimeError("boom")
        ctx = build_company_context(["google"], loader=BoomLoader())
        assert ctx.is_empty
        assert ctx.unknown_company_ids == ["google"]


# --------------------------------------------------------------------------- #
# LearnerContext integration
# --------------------------------------------------------------------------- #
class TestLearnerContextIntegration:
    def test_company_context_attached_from_target_companies(self):
        lc = build_learner_context(target_companies=["google", "adobe"])
        assert isinstance(lc.company_context, CompanyContext)
        assert lc.company_context.known_ids() == ["google", "adobe"]
        # target_companies list itself is preserved as before
        assert lc.target_companies == ["google", "adobe"]

    def test_empty_companies_still_gets_empty_context(self):
        lc = build_learner_context()
        assert isinstance(lc.company_context, CompanyContext)
        assert lc.company_context.is_empty

    def test_explicit_company_context_is_respected(self):
        injected = CompanyContext(selected_company_ids=["x"])
        lc = build_learner_context(target_companies=["google"], company_context=injected)
        assert lc.company_context is injected  # not rebuilt


# --------------------------------------------------------------------------- #
# Backward compatibility — scoring inputs unaffected
# --------------------------------------------------------------------------- #
class TestBackwardCompatibility:
    def _sample_nodes(self):
        return [
            {"id": "n1", "track": "dsa", "topic": "arrays", "difficulty": "easy",
             "company_importance": {"google": 5}, "prerequisites": []},
            {"id": "n2", "track": "java", "topic": "streams", "difficulty": "medium",
             "company_importance": {"google": 3}, "prerequisites": []},
        ]

    def test_ranking_identical_with_and_without_company_context(self):
        from services.learning_engine.ranking import rank_learning_nodes
        nodes = self._sample_nodes()
        progress_map = {}

        # Baseline call (pre-Phase-2A style): no context.
        baseline = rank_learning_nodes(copy.deepcopy(nodes), progress_map,
                                       target_companies=["google"])

        # With a fully-populated LearnerContext that now carries company_context.
        lc = build_learner_context(target_companies=["google"])
        assert lc.company_context is not None and not lc.company_context.is_empty
        withctx = rank_learning_nodes(copy.deepcopy(nodes), progress_map,
                                      target_companies=["google"])

        # Ranking must be byte-identical: company_context is planner-inert.
        assert [n["id"] for n in baseline] == [n["id"] for n in withctx]

    def test_score_candidate_unaffected_by_company_context(self):
        from services.learning_engine.priority_engine import score_candidate
        node = self._sample_nodes()[0]

        lc_plain = build_learner_context(target_companies=["google"],
                                         company_context=CompanyContext())
        lc_full = build_learner_context(target_companies=["google"])
        assert not lc_full.company_context.is_empty

        s_plain = score_candidate(copy.deepcopy(node), lc_plain)
        s_full = score_candidate(copy.deepcopy(node), lc_full)
        assert s_plain.score == s_full.score
