"""Phase 3C.1 — activity_type / assessment_type curriculum metadata.

Pure unit tests (no server / DB). Verify the roadmap was stamped, the
derivation is deterministic + idempotent, and the enums/mapping are frozen.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from roadmap import get_roadmap  # noqa: E402
from services.curriculum.activity_metadata import (  # noqa: E402
    ACTIVITY_TYPES, ASSESSMENT_TYPES, ACTIVITY_TO_ASSESSMENT,
    TRACK_ACTIVITY_TYPE, derive_activity_type, derive_assessment_type, stamp_node,
)


def test_every_roadmap_node_declares_activity_and_assessment_type():
    r = get_roadmap()
    missing = []
    for node in r.all_nodes():
        at = node.get("activity_type")
        st = node.get("assessment_type")
        if at not in ACTIVITY_TYPES or st not in ASSESSMENT_TYPES:
            missing.append((node.get("id"), at, st))
    assert not missing, f"nodes missing/invalid activity metadata: {missing[:10]}"


def test_known_nodes_have_expected_types():
    r = get_roadmap()
    cases = {
        "dsa.foundations.arrays": ("coding", "coding"),
        "pf.intro.core": ("study", "quiz"),
        "behavioral.framework.star": ("behavioral", "behavioral"),
        "hld.foundations.scalability": ("system_design", "system_design"),
    }
    for nid, (at, st) in cases.items():
        node = r.get(nid)
        assert node, f"{nid} should resolve"
        assert node["activity_type"] == at, (nid, node["activity_type"])
        assert node["assessment_type"] == st, (nid, node["assessment_type"])


def test_derivation_is_deterministic_and_idempotent():
    node = {"tags": []}
    a1 = derive_activity_type(node, "dsa")
    a2 = derive_activity_type(node, "dsa")
    assert a1 == a2 == "coding"
    stamp_node(node, "dsa")
    before = dict(node)
    stamp_node(node, "dsa")  # second run must not change anything
    assert node == before


def test_explicit_value_is_respected():
    node = {"activity_type": "flashcards"}
    assert derive_activity_type(node, "dsa") == "flashcards"
    assert derive_assessment_type(node, "dsa", "flashcards") == "quiz"


def test_assessment_mapping_matches_frozen_contract():
    assert ACTIVITY_TO_ASSESSMENT["coding"] == "coding"
    assert ACTIVITY_TO_ASSESSMENT["study"] == "quiz"
    assert ACTIVITY_TO_ASSESSMENT["behavioral"] == "behavioral"
    assert ACTIVITY_TO_ASSESSMENT["design"] == "design"
    assert ACTIVITY_TO_ASSESSMENT["system_design"] == "system_design"


def test_every_real_track_is_mapped():
    r = get_roadmap()
    for track in r.tracks():
        assert track["id"] in TRACK_ACTIVITY_TYPE, f"{track['id']} not mapped"
