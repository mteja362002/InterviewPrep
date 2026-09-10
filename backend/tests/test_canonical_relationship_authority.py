"""Canonical roadmap relationships must stay authoritative over AI output.

Regression for a defect found during the sprint verification gate.
``_merge_relationships`` previously placed AI-generated entries FIRST and let
them win id collisions ("AI-generated entries take priority; deterministic fill
gaps"), which allowed a model response to redefine, reorder ahead of, or
silently replace an authored prerequisite/related edge.

Required hierarchy:

    canonical roadmap prerequisites  ->  authoritative
    AI suggestions                   ->  supplementary / enrichment
"""
from knowledge_generation import _deterministic_related, _merge_relationships


class FakeRoadmap:
    """Minimal stand-in exposing the ``.get`` contract the helper relies on."""

    def __init__(self, nodes):
        self._nodes = nodes

    def get(self, node_id):
        return self._nodes.get(node_id)


CANONICAL = {
    "related_topics": [
        {"id": "arrays", "label": "Arrays", "why": "Related topic in the roadmap.",
         "source": "roadmap"},
    ],
    "prerequisites": [
        {"id": "big-o", "label": "Big-O Notation", "why": "Prerequisite in the roadmap.",
         "source": "roadmap"},
    ],
}


class TestCanonicalAuthority:

    def test_ai_cannot_redefine_a_canonical_prerequisite(self):
        """An AI entry colliding on id must be dropped, not merged over."""
        parsed = {"prerequisites": [
            {"id": "big-o", "label": "AI's Big O", "why": "AI rewrote this."},
        ]}
        out = _merge_relationships(CANONICAL, parsed)
        assert out["prerequisites"] == CANONICAL["prerequisites"]
        assert out["prerequisites"][0]["label"] == "Big-O Notation"
        assert out["prerequisites"][0]["source"] == "roadmap"

    def test_ai_cannot_redefine_a_canonical_related_topic(self):
        parsed = {"related_topics": [
            {"id": "arrays", "label": "AI Arrays", "why": "AI rewrote this."},
        ]}
        out = _merge_relationships(CANONICAL, parsed)
        assert out["related_topics"] == CANONICAL["related_topics"]

    def test_canonical_entries_come_first(self):
        """Ordering is part of authority — canonical must outrank AI."""
        parsed = {
            "related_topics": [{"id": "z-extra", "label": "Extra"}],
            "prerequisites": [{"id": "z-prereq", "label": "Extra Prereq"}],
        }
        out = _merge_relationships(CANONICAL, parsed)
        assert out["related_topics"][0]["id"] == "arrays"
        assert out["prerequisites"][0]["id"] == "big-o"

    def test_ai_only_entries_are_kept_as_supplementary(self):
        """Enrichment still works — AI may ADD edges the roadmap lacks."""
        parsed = {"prerequisites": [{"id": "recursion", "label": "Recursion"}]}
        out = _merge_relationships(CANONICAL, parsed)
        ids = [p["id"] for p in out["prerequisites"]]
        assert ids == ["big-o", "recursion"]
        assert out["prerequisites"][1]["source"] == "ai"

    def test_empty_ai_output_leaves_canonical_intact(self):
        for parsed in ({}, {"prerequisites": [], "related_topics": []},
                       {"prerequisites": None, "related_topics": None}):
            out = _merge_relationships(CANONICAL, parsed)
            assert out["prerequisites"] == CANONICAL["prerequisites"]
            assert out["related_topics"] == CANONICAL["related_topics"]

    def test_ai_cannot_empty_the_canonical_list(self):
        """No AI response shape may reduce the canonical set."""
        out = _merge_relationships(CANONICAL, {"prerequisites": []})
        assert len(out["prerequisites"]) == len(CANONICAL["prerequisites"])

    def test_merge_is_deterministic(self):
        parsed = {"prerequisites": [{"id": "recursion", "label": "Recursion"}]}
        assert _merge_relationships(CANONICAL, parsed) == \
            _merge_relationships(CANONICAL, parsed)

    def test_canonical_entries_are_sourced_from_the_roadmap(self):
        """`_deterministic_related` must stamp provenance on every entry."""
        roadmap = FakeRoadmap({
            "big-o": {"id": "big-o", "label": "Big-O Notation"},
            "arrays": {"id": "arrays", "label": "Arrays"},
        })
        node = {"id": "sorting", "prerequisites": ["big-o"], "related": ["arrays"]}
        out = _deterministic_related(node, roadmap)
        assert out["prerequisites"][0]["source"] == "roadmap"
        assert out["related_topics"][0]["source"] == "roadmap"

    def test_unknown_canonical_ids_are_dropped_not_invented(self):
        """A prerequisite id absent from the pinned roadmap yields no entry."""
        roadmap = FakeRoadmap({})
        node = {"id": "sorting", "prerequisites": ["does-not-exist"], "related": []}
        out = _deterministic_related(node, roadmap)
        assert out["prerequisites"] == []
