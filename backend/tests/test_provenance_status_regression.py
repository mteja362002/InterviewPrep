"""Regression test: _derive_subject_status must distinguish provenance correctly.

Three provenance tiers must remain distinct:
  - certified_actual   → "completed" (actual curriculum traversal)
  - onboarding_baseline → "effectively_completed" (declared only)
  - unverified_legacy   → "effectively_completed" (not certified)
  - None / missing      → "effectively_completed" (not certified)

An unverified_legacy row must NEVER be treated as certified_actual.
"""
import pytest
from services.evidence import certified_fields, planner_row
from services.learning_engine.subject_progression import _derive_subject_status


def _make_nodes(track_id, count=3):
    """Create minimal node dicts for testing."""
    return [{"id": f"{track_id}.node.{i}", "track": track_id} for i in range(count)]


def _make_progress(nodes, status="completed", source=None):
    """Create a progress_map where all nodes have the given status and source."""
    pm = {}
    for n in nodes:
        entry = {"status": status}
        if source is not None:
            entry["planner_progress_source"] = source
        pm[n["id"]] = entry
    return pm


class TestProvenanceDistinction:
    """Prove that effectively_completed, completed, and mastered remain distinct
    based on provenance, and that unverified_legacy is NOT treated as certified."""

    TRACK = "java"
    PREREQS = ["programming_fundamentals"]
    # completed_subjects must include the track AND its prerequisites
    # for Gate 1 (prereq check) and Gate 1.5 (completion check) to fire.
    COMPLETED_SUBJECTS = {TRACK, "programming_fundamentals"}

    def _derive(self, progress_map):
        nodes = _make_nodes(self.TRACK)
        return _derive_subject_status(
            self.TRACK, self.PREREQS, self.COMPLETED_SUBJECTS, nodes, progress_map,
        )

    def test_all_certified_actual_returns_completed(self):
        """When all nodes have certified_actual provenance → 'completed'."""
        nodes = _make_nodes(self.TRACK)
        pm = _make_progress(nodes, "completed", source="certified_actual")
        # Not all_done (some node has a status that's in completed set) but has certified
        # Actually for this to hit has_actual_completion, not all_done must be False.
        # Make one node NOT completed so all_done is False, but one node IS completed with certified
        pm[nodes[2]["id"]]["status"] = "in_progress"
        assert self._derive(pm) == "completed"

    def test_all_onboarding_baseline_returns_effectively_completed(self):
        """When all completed nodes have onboarding_baseline → 'effectively_completed'."""
        nodes = _make_nodes(self.TRACK)
        pm = _make_progress(nodes, "completed", source="onboarding_baseline")
        pm[nodes[2]["id"]]["status"] = "in_progress"
        assert self._derive(pm) == "effectively_completed"

    def test_unverified_legacy_returns_effectively_completed(self):
        """CRITICAL: unverified_legacy must NOT be treated as certified_actual.
        If a learner has only unverified_legacy rows, the track should be
        'effectively_completed', not 'completed'.
        """
        nodes = _make_nodes(self.TRACK)
        pm = _make_progress(nodes, "completed", source="unverified_legacy")
        pm[nodes[2]["id"]]["status"] = "in_progress"
        assert self._derive(pm) == "effectively_completed"

    def test_missing_provenance_returns_effectively_completed(self):
        """Rows with no planner_progress_source field at all (None) must NOT
        be treated as certified_actual."""
        nodes = _make_nodes(self.TRACK)
        pm = _make_progress(nodes, "completed", source=None)
        # source=None means the key is not set in the dict
        for nid in pm:
            pm[nid].pop("planner_progress_source", None)
        pm[nodes[2]["id"]]["status"] = "in_progress"
        assert self._derive(pm) == "effectively_completed"

    def test_empty_string_provenance_returns_effectively_completed(self):
        """Rows with planner_progress_source="" must NOT be treated as
        certified_actual."""
        nodes = _make_nodes(self.TRACK)
        pm = _make_progress(nodes, "completed", source="")
        pm[nodes[2]["id"]]["status"] = "in_progress"
        assert self._derive(pm) == "effectively_completed"

    def test_mixed_certified_and_onboarding_returns_completed(self):
        """If ANY node has certified_actual, the track is 'completed'."""
        nodes = _make_nodes(self.TRACK)
        pm = {}
        pm[nodes[0]["id"]] = {"status": "completed", "planner_progress_source": "certified_actual"}
        pm[nodes[1]["id"]] = {"status": "completed", "planner_progress_source": "onboarding_baseline"}
        pm[nodes[2]["id"]] = {"status": "in_progress"}
        assert self._derive(pm) == "completed"

    def test_mixed_legacy_and_onboarding_returns_effectively_completed(self):
        """Legacy + onboarding but NO certified → 'effectively_completed'."""
        nodes = _make_nodes(self.TRACK)
        pm = {}
        pm[nodes[0]["id"]] = {"status": "completed", "planner_progress_source": "unverified_legacy"}
        pm[nodes[1]["id"]] = {"status": "completed", "planner_progress_source": "onboarding_baseline"}
        pm[nodes[2]["id"]] = {"status": "in_progress"}
        assert self._derive(pm) == "effectively_completed"

    def test_all_nodes_done_all_certified_returns_mastered(self):
        """When ALL nodes are completed (regardless of source) → 'mastered'."""
        nodes = _make_nodes(self.TRACK)
        pm = _make_progress(nodes, "completed", source="certified_actual")
        assert self._derive(pm) == "mastered"

    def test_all_nodes_done_all_onboarding_returns_mastered(self):
        """When ALL nodes are completed via onboarding → 'mastered'.
        (all_done check fires before has_actual_completion.)"""
        nodes = _make_nodes(self.TRACK)
        pm = _make_progress(nodes, "completed", source="onboarding_baseline")
        assert self._derive(pm) == "mastered"


class TestPlannerStampIsEarnedByStatusField:
    """The row-level stamp must be earned by the ``status`` field specifically.

    Regression for a laundering path found during the sprint verification gate.
    Three production writers certify fields *without* certifying status:

      * ``revision_engine.mark_node_for_revision``  -> next_revision, revision_stage
      * ``routes_missions`` revise-task completion   -> last_revision
      * ``routes_roadmap`` attempt endpoint          -> attempts (increment)

    ``planner_row`` previously stamped ``certified_actual`` whenever the row had
    *any* certified field. A node carrying a historical UNVERIFIED_LEGACY
    ``status="completed"`` would therefore be promoted to certified actual
    completion the first time the learner recorded an attempt — and the planner
    would stop scheduling the track. The per-field stamps in ``certified_fields``
    exist precisely to prevent this; the stamp must respect them.
    """

    TRACK = "java"
    PREREQS = ["programming_fundamentals"]
    COMPLETED_SUBJECTS = {TRACK, "programming_fundamentals"}

    @staticmethod
    def _legacy_completed_row(node_id, certified=None, sources=None):
        """A historical row whose top-level completion was never certified."""
        row = {
            "node_id": node_id,
            "status": "completed",
            "planner_progress_source": "unverified_legacy",
        }
        if certified:
            row["certified_progress"] = {
                **certified,
                "field_sources": {
                    key: {"source": src, "recorded_at": "2026-09-09T12:00:00Z"}
                    for key, src in (sources or {}).items()
                },
            }
        return row

    def _derive_from(self, rows):
        nodes = _make_nodes(self.TRACK)
        pm = {}
        for node, row in zip(nodes, rows):
            pm[node["id"]] = planner_row({**row, "node_id": node["id"]})
        # Leave the last node incomplete so the all_done/mastered gate cannot fire.
        pm[nodes[-1]["id"]] = {"status": "in_progress"}
        return _derive_subject_status(
            self.TRACK, self.PREREQS, self.COMPLETED_SUBJECTS, nodes, pm,
        )

    @pytest.mark.parametrize("certified,sources", [
        ({"attempts": 3}, {"attempts": "attempt"}),
        ({"actual_solve_minutes": 42}, {"actual_solve_minutes": "attempt"}),
        ({"next_revision": "2026-10-01", "revision_stage": 1},
         {"next_revision": "revision", "revision_stage": "revision"}),
        ({"last_revision": "2026-09-09"}, {"last_revision": "revision"}),
        ({"confidence": 4}, {"confidence": "confidence_update"}),
    ])
    def test_non_status_certification_does_not_earn_actual_stamp(self, certified, sources):
        """Certifying a non-status field must leave the legacy stamp intact."""
        row = self._legacy_completed_row("n1", certified, sources)
        stamped = planner_row(row)
        assert "status" not in certified_fields(row)
        assert stamped["planner_progress_source"] == "unverified_legacy"

    @pytest.mark.parametrize("certified,sources", [
        ({"attempts": 3}, {"attempts": "attempt"}),
        ({"next_revision": "2026-10-01"}, {"next_revision": "revision"}),
        ({"confidence": 4}, {"confidence": "confidence_update"}),
    ])
    def test_legacy_completion_survives_unrelated_certified_write(self, certified, sources):
        """End-to-end: the track must stay effectively_completed, not completed."""
        rows = [self._legacy_completed_row("n0", certified, sources),
                self._legacy_completed_row("n1")]
        assert self._derive_from(rows) == "effectively_completed"

    def test_certified_status_still_earns_actual_stamp(self):
        """A genuine certified completion must NOT be demoted by this rule."""
        row = self._legacy_completed_row(
            "n1", {"status": "completed"}, {"status": "task_completion"},
        )
        assert planner_row(row)["planner_progress_source"] == "certified_actual"

    def test_certified_status_still_resolves_to_completed(self):
        """The positive path is preserved end-to-end."""
        rows = [self._legacy_completed_row(
            "n0", {"status": "completed"}, {"status": "task_completion"}), {}]
        assert self._derive_from(rows) == "completed"

    def test_onboarding_baseline_stamp_is_preserved_not_downgraded(self):
        """A baseline row keeps its own stamp; it must not become legacy."""
        row = {
            "node_id": "n1",
            "status": "completed",
            "planner_progress_source": "onboarding_baseline",
            "certified_progress": {
                "attempts": 1,
                "field_sources": {
                    "attempts": {"source": "attempt",
                                 "recorded_at": "2026-09-09T12:00:00Z"},
                },
            },
        }
        assert planner_row(row)["planner_progress_source"] == "onboarding_baseline"
