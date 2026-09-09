from unittest.mock import patch

from roadmap import RoadmapEngine
from services.progress_engine import build_canonical_progress
from tests.evidence_fixtures import certified


class FakeRoadmap:
    version = "v1"
    def __init__(self):
        self._nodes = {
            "root": {"id": "root", "child_ids": ["module"]},
            "module": {"id": "module", "child_ids": ["leaf"]},
            "leaf": {"id": "leaf", "child_ids": []},
        }

    def get(self, node_id):
        return self._nodes.get(node_id)

    def children(self, node_id):
        node = self.get(node_id)
        if not node:
            return []
        return [self.get(child_id) for child_id in node.get("child_ids", []) if self.get(child_id)]

    def tracks(self):
        return [self.get("root")]


def test_canonical_progress_rolls_up_from_children():
    roadmap = FakeRoadmap()
    progress_rows = {
        "leaf": {
            "status": "completed",
            "confidence": 9.0,
            "weakness_score": 10.0,
            "mastery_percentage": 80.0,
        }
    }

    result = build_canonical_progress(roadmap, {nid: certified(row) for nid, row in progress_rows.items()})

    assert result["module"]["completed_topics"] == 1
    assert result["module"]["total_topics"] == 1
    assert result["module"]["completion_pct"] == 100.0
    assert result["root"]["completed_topics"] == 1
    assert result["root"]["total_topics"] == 1


def test_canonical_progress_walks_real_track_roots():
    class TrackRoadmap(FakeRoadmap):
        def __init__(self):
            super().__init__()
            self._nodes = {
                "dsa": {"id": "dsa", "child_ids": ["module"]},
                "module": {"id": "module", "child_ids": ["leaf"]},
                "leaf": {"id": "leaf", "child_ids": []},
            }

        def tracks(self):
            return [self.get("dsa")]

    roadmap = TrackRoadmap()
    progress_rows = {
        "leaf": {
            "status": "completed",
            "confidence": 9.0,
            "weakness_score": 10.0,
            "mastery_percentage": 80.0,
        }
    }

    result = build_canonical_progress(roadmap, {nid: certified(row) for nid, row in progress_rows.items()})

    assert result["module"]["completion_pct"] == 100.0
    assert result["dsa"]["completion_pct"] == 100.0


def test_roadmap_parser_walks_generic_nested_containers():
    raw = {
        "tracks": [
            {
                "id": "track",
                "label": "Track",
                "sections": [
                    {
                        "id": "section",
                        "label": "Section",
                        "categories": [
                            {
                                "id": "category",
                                "label": "Category",
                                "modules": [
                                    {
                                        "id": "module",
                                        "label": "Module",
                                        "topics": [
                                            {
                                                "id": "topic",
                                                "label": "Topic",
                                                "learning_nodes": [
                                                    {"id": "node", "label": "Node"}
                                                ],
                                            }
                                        ],
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ]
    }

    with patch.object(RoadmapEngine, "_load", return_value=raw):
        engine = RoadmapEngine("v1")

    assert engine.get("section") is not None
    assert engine.get("category") is not None
    assert engine.get("module") is not None
    assert engine.get("topic") is not None
    assert engine.get("node") is not None
    assert engine.children("track") == [engine.get("section")]
    assert engine.children("section") == [engine.get("category")]
    assert engine.children("category") == [engine.get("module")]
    assert engine.children("module") == [engine.get("topic")]
    assert engine.children("topic") == [engine.get("node")]


def test_canonical_progress_counts_only_learning_nodes():
    engine = RoadmapEngine("v1")
    result = build_canonical_progress(engine, {})
    for track in engine.tracks():
        rollup = result.get(track["id"])
        assert rollup is not None
        assert rollup["total_topics"] > 0


def test_canonical_progress_partial_completion_is_not_completed():
    """One completed child out of many untouched siblings must report
    'in_progress', never 'completed' — regression test for a bug where
    filtering out not_started children before all() made a single
    completed leaf vacuously satisfy the "all completed" check."""

    class SectionRoadmap(FakeRoadmap):
        def __init__(self):
            self._nodes = {
                "section": {"id": "section", "child_ids": ["a", "b", "c", "d", "e"]},
                "a": {"id": "a", "child_ids": []},
                "b": {"id": "b", "child_ids": []},
                "c": {"id": "c", "child_ids": []},
                "d": {"id": "d", "child_ids": []},
                "e": {"id": "e", "child_ids": []},
            }

        def tracks(self):
            return [self.get("section")]

    roadmap = SectionRoadmap()
    progress_rows = {"a": {"status": "completed", "mastery_percentage": 80.0}}

    result = build_canonical_progress(roadmap, {nid: certified(row) for nid, row in progress_rows.items()})

    assert result["section"]["completed_topics"] == 1
    assert result["section"]["total_topics"] == 5
    assert result["section"]["status"] == "in_progress"


def test_canonical_progress_fully_untouched_section_is_not_started():
    class SectionRoadmap(FakeRoadmap):
        def __init__(self):
            self._nodes = {
                "section": {"id": "section", "child_ids": ["a", "b"]},
                "a": {"id": "a", "child_ids": []},
                "b": {"id": "b", "child_ids": []},
            }

        def tracks(self):
            return [self.get("section")]

    roadmap = SectionRoadmap()
    result = build_canonical_progress(roadmap, {})

    assert result["section"]["status"] == "not_started"


def test_canonical_progress_all_children_completed_is_completed():
    class SectionRoadmap(FakeRoadmap):
        def __init__(self):
            self._nodes = {
                "section": {"id": "section", "child_ids": ["a", "b"]},
                "a": {"id": "a", "child_ids": []},
                "b": {"id": "b", "child_ids": []},
            }

        def tracks(self):
            return [self.get("section")]

    roadmap = SectionRoadmap()
    progress_rows = {
        "a": {"status": "completed", "mastery_percentage": 100.0},
        "b": {"status": "mastered", "mastery_percentage": 100.0},
    }

    result = build_canonical_progress(roadmap, {nid: certified(row) for nid, row in progress_rows.items()})

    assert result["section"]["status"] == "completed"
