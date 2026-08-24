"""Roadmap Engine — the single source of truth for topic hierarchy.

The master roadmap is loaded from `data/roadmap_v{N}.json`. This engine
exposes O(1) node lookup, tree traversal, prerequisite resolution and
company-importance queries. Every other module (Mission Engine, Coding
Arena, Knowledge Base, Company Readiness, future AI Mentor) should read
from here — never redefine topic strings.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional, List, Dict, Iterable
from functools import lru_cache

_DATA_DIR = Path(__file__).parent / "data"
CURRENT_VERSION = "v1"


class RoadmapNode(dict):
    """Lightweight dict subclass for readability. Never mutate."""


def _infer_child_type(key: str) -> str:
    """Translate a container key into a node type for the roadmap tree."""
    if key in {"modules", "module"}:
        return "module"
    if key in {"topics", "topic"}:
        return "topic"
    if key in {"subtopics", "subtopic"}:
        return "subtopic"
    if key in {"learning_nodes", "learning_node", "node", "nodes"}:
        return "node"
    if key in {"sections", "section"}:
        return "section"
    if key in {"categories", "category"}:
        return "category"
    if key.endswith("ies") and len(key) > 4:
        return key[:-3] + "y"
    if key.endswith("s") and len(key) > 1:
        return key[:-1]
    return key


def _flatten(node: dict, parent_id: Optional[str], depth: int,
             out: Dict[str, dict], type_hint: str, track_id: Optional[str] = None) -> None:
    """Walk the roadmap JSON, tagging each node with parent/depth/type/children."""
    node["type"] = type_hint
    node["parent_id"] = parent_id
    node["depth"] = depth
    node["child_ids"] = []
    if track_id:
        node["track"] = track_id

    if type_hint == "node":
        out[node["id"]] = node
        return

    for key, value in node.items():
        if not isinstance(value, list):
            continue
        if not value or not all(isinstance(item, dict) for item in value):
            continue
        child_type = _infer_child_type(key)
        for child in value:
            child_id = child.get("id")
            if not child_id:
                continue
            node["child_ids"].append(child_id)
            _flatten(child, parent_id=node["id"], depth=depth + 1, out=out, type_hint=child_type, track_id=track_id or node.get("id"))

    out[node["id"]] = node


class RoadmapEngine:
    def __init__(self, version: str = CURRENT_VERSION):
        self.version = version
        self._raw = self._load(version)
        self._index: Dict[str, dict] = {}
        self._by_pattern: Dict[str, List[dict]] = {}
        for track in self._raw["tracks"]:
            track_id = track.get("id")
            _flatten(track, parent_id=None, depth=0, out=self._index, type_hint="track", track_id=track_id)
        for node in self._index.values():
            pat = node.get("pattern")
            if pat:
                self._by_pattern.setdefault(pat, []).append(node)

    @staticmethod
    def _load(version: str) -> dict:
        f = _DATA_DIR / f"roadmap_{version}.json"
        with open(f, "r", encoding="utf-8") as fh:
            return json.load(fh)

    # ---------- Tree APIs ----------
    def tree(self) -> dict:
        return {
            "version": self.version,
            "companies": self._raw.get("companies", []),
            "tracks": self._raw["tracks"],
        }

    def get(self, node_id: str) -> Optional[dict]:
        return self._index.get(node_id)

    def all_nodes(self) -> Iterable[dict]:
        return self._index.values()

    def children(self, node_id: str) -> List[dict]:
        n = self.get(node_id)
        if not n:
            return []
        return [self._index[c] for c in n.get("child_ids", []) if c in self._index]

    def ancestors(self, node_id: str) -> List[dict]:
        """Root-to-node breadcrumb (excludes the node itself)."""
        path = []
        cur = self.get(node_id)
        while cur and cur.get("parent_id"):
            parent = self.get(cur["parent_id"])
            if parent:
                path.append(parent)
                cur = parent
            else:
                break
        return list(reversed(path))

    def find_track(self, node_id: str) -> Optional[dict]:
        cur = self.get(node_id)
        if not cur:
            return None
        while cur and cur.get("parent_id"):
            cur = self.get(cur["parent_id"])
        return cur

    # ---------- Metadata ----------
    def prerequisites(self, node_id: str) -> List[dict]:
        n = self.get(node_id)
        if not n:
            return []
        result = []
        for pid in n.get("prerequisites", []) or []:
            p = self.get(pid)
            if p:
                result.append(p)
        return result

    def related(self, node_id: str) -> List[dict]:
        n = self.get(node_id)
        if not n:
            return []
        result = []
        for rid in n.get("related", []) or []:
            r = self.get(rid)
            if r:
                result.append(r)
        return result

    def by_pattern(self, pattern: str) -> List[dict]:
        return self._by_pattern.get(pattern, [])

    def topic_for_pattern(self, pattern: str) -> Optional[dict]:
        nodes = self._by_pattern.get(pattern, [])
        return nodes[0] if nodes else None

    def pattern_for_node(self, node_id: str) -> Optional[str]:
        """Return the interview pattern for a node, inherited from the nearest
        ancestor topic that declares one.

        `pattern` is authored once per topic (e.g. ``dsa.windows.sliding_window``)
        rather than duplicated on every leaf learning node, so a leaf-level
        recommendation (e.g. "Minimum Window Substring") must walk up the tree
        to find it instead of relying on a legacy label-keyed lookup table.
        """
        node = self.get(node_id)
        if not node:
            return None
        if node.get("pattern"):
            return node["pattern"]
        for ancestor in reversed(self.ancestors(node_id)):
            if ancestor.get("pattern"):
                return ancestor["pattern"]
        return None

    def problems_for_node(self, node_id: str) -> List[str]:
        n = self.get(node_id)
        if not n:
            return []
        # Aggregate problem_ids from this node + descendants
        pids: List[str] = list(n.get("problem_ids", []) or [])
        for c_id in n.get("child_ids", []):
            pids.extend(self.problems_for_node(c_id))
        return pids

    def company_importance(self, node_id: str, company_id: str) -> int:
        """Return the 0-5 company-importance rating for ``node_id``.

        RC1.3.1 · Hierarchical inheritance:
            LearningNode → Topic → Module → Track
        The first level (walking up the tree) that declares an entry for
        ``company_id`` wins. This lets roadmap authors override at any
        granularity — a single subtopic can bump Google to 5 stars without
        touching the whole track — while still degrading gracefully for
        older roadmap files that only carried track-level data.

        Backward compatible with the previous two-level (node → track)
        fallback: if only track-level data exists (older roadmap files),
        behaviour is unchanged.
        """
        n = self.get(node_id)
        if not n:
            return 0
        # Walk from the node up through every ancestor (nearest first) and
        # finally the track. `ancestors` already returns root-to-node, so we
        # reverse it to get node → topic → module → … → track.
        chain = [n] + list(reversed(self.ancestors(node_id)))
        for src in chain:
            ci = src.get("company_importance") if src else None
            if ci and company_id in ci:
                try:
                    return int(ci[company_id])
                except (TypeError, ValueError):
                    return 0
        return 0

    def company_importance_chain(self, node_id: str, company_id: str) -> Optional[dict]:
        """Introspection helper — return which ancestor supplied the score.

        Returns {"level": "topic|module|track|node", "source_id": str, "value": int}
        or None if nothing in the chain declared a rating for the company.
        Not used by the ranking engine — kept purely for debugging /
        future UI ("importance inherited from Track: DSA").
        """
        n = self.get(node_id)
        if not n:
            return None
        chain = [n] + list(reversed(self.ancestors(node_id)))
        for src in chain:
            ci = src.get("company_importance") if src else None
            if ci and company_id in ci:
                try:
                    val = int(ci[company_id])
                except (TypeError, ValueError):
                    continue
                return {
                    "level": src.get("type", "unknown"),
                    "source_id": src.get("id"),
                    "value": val,
                }
        return None

    def tracks(self) -> List[dict]:
        return list(self._raw["tracks"])

    def track_ids(self) -> List[str]:
        return [t["id"] for t in self._raw["tracks"]]

    # ---------- Curriculum Sync DAG metadata (Phase 3) ----------
    # `subject_prerequisites` / `module_prerequisites` / `topic_prerequisites`
    # are stamped on every track/module/topic by
    # `scripts/generate_roadmap.py::_annotate_curriculum_sync_metadata`.
    # These accessors let runtime code DERIVE subject/module/topic ordering
    # and eligibility straight from that metadata instead of re-encoding a
    # parallel hardcoded chain/list — the single-source-of-truth contract
    # Curriculum Sync Phase 3 requires.

    def subjects_without_prerequisites(self) -> List[str]:
        """Track ids whose `subject_prerequisites` list is empty.

        This is exactly the set of subjects with nothing upstream in the DAG:
        the true root of the academic chain (Programming Fundamentals) plus
        every subject deliberately isolated from it (Projects, Resume &
        LinkedIn, Behavioral). Used to derive — instead of hardcode — which
        tracks must never receive an inherited/default onboarding baseline.
        """
        return [t["id"] for t in self._raw["tracks"] if not (t.get("subject_prerequisites") or [])]

    def root_subject_ids(self) -> List[str]:
        """Track ids that start the academic DAG: no `subject_prerequisites`
        of their own, but they DO unlock at least one other subject. This
        distinguishes the true entry point(s) (e.g. Programming Fundamentals)
        from subjects that are simply isolated from the DAG entirely
        (Projects/Resume/Behavioral, which unlock nothing)."""
        return [
            t["id"]
            for t in self._raw["tracks"]
            if (
                not (t.get("subject_prerequisites") or [])
                and t.get("modules")
                and (t.get("subject_unlocks") or [])
            )
        ]

    def is_subject_unlocked(self, track_id: str, completed_subject_ids: Iterable[str] = ()) -> bool:
        """Return whether every prerequisite subject in the DAG is satisfied.

        Supports multiple prerequisites (e.g. HLD requires Java, DBMS,
        Operating Systems, Computer Networks AND LLD all at once) — a subject
        is eligible only once ALL of its `subject_prerequisites` are present
        in `completed_subject_ids`, not just any one of them.
        """
        track = self.get(track_id)
        if not track:
            return False
        completed = set(completed_subject_ids)
        return all(pre in completed for pre in track.get("subject_prerequisites") or [])

    def is_module_unlocked(self, module_id: str, completed_module_ids: Iterable[str] = ()) -> bool:
        """Return whether every prerequisite module in the DAG is satisfied."""
        module = self.get(module_id)
        if not module:
            return False
        completed = set(completed_module_ids)
        return all(pre in completed for pre in module.get("module_prerequisites") or [])

    def is_topic_unlocked(self, topic_id: str, completed_topic_ids: Iterable[str] = ()) -> bool:
        """Return whether every prerequisite topic in the DAG is satisfied."""
        topic = self.get(topic_id)
        if not topic:
            return False
        completed = set(completed_topic_ids)
        return all(pre in completed for pre in topic.get("topic_prerequisites") or [])

    # ---------- Subject-gate filters (Curriculum Progression Engine) ----------

    def completed_subject_ids(self, completed_nodes: Iterable[str]) -> List[str]:
        """Return track IDs where all foundation+core learning nodes are done.

        A subject is "completed for prerequisite purposes" when every
        learning node with ``learning_stage ∈ {foundation, core}`` has a
        matching entry in *completed_nodes*.  Advanced/interview nodes
        are depth, not breadth — they are NOT required for gating.

        This is the exact derivation consumed by
        ``get_curriculum_eligible_nodes`` and the Subject Progression
        Engine to enforce subject-level prerequisites without introducing
        a separate stored "subject completion" flag.
        """
        completed = set(completed_nodes)
        result: List[str] = []
        for track in self._raw["tracks"]:
            track_id = track["id"]
            fc_nodes = [
                n for n in self.get_track_learning_nodes(track_id)
                if n.get("learning_stage") in ("foundation", "core", None)
            ]
            if not fc_nodes:
                # Tracks with no learning nodes at all (structural only)
                # cannot be "completed" — skip.
                continue
            if all(n["id"] in completed for n in fc_nodes):
                result.append(track_id)
        return result

    def get_curriculum_eligible_nodes(
        self, completed_nodes: Iterable[str],
    ) -> List[dict]:
        """Return learning nodes passing BOTH subject-gate AND node-gate.

        Two-layer filter:
        1. **Subject gate** — the node's track must have its
           ``subject_prerequisites`` satisfied (checked via
           ``completed_subject_ids``).
        2. **Node gate** — the node's own ``prerequisites`` must be
           satisfied (existing ``is_unlocked`` logic).

        Tracks with no ``subject_prerequisites`` (e.g. Programming
        Fundamentals, Behavioral) pass the subject gate unconditionally.
        """
        completed = set(completed_nodes)
        done_subjects = set(self.completed_subject_ids(completed))
        result: List[dict] = []
        for node in self.get_learning_nodes():
            track_id = node.get("track")
            track = self.get(track_id) if track_id else None
            # Subject gate: track prerequisites must all be completed subjects
            if track:
                subj_prereqs = track.get("subject_prerequisites") or []
                if not all(sp in done_subjects for sp in subj_prereqs):
                    continue
            # Node gate: node-level prerequisites
            if not self.is_unlocked(node["id"], completed):
                continue
            result.append(node)
        return result

    # ---------- Learning-node traversal ----------
    @staticmethod
    def _is_learning_node(node: dict) -> bool:
        """Return whether ``node`` is an atomic learning unit.

        Most tracks (Java, HLD, Operating Systems, DBMS, Computer Networks,
        Behavioral, Projects, Resume) put prerequisites/mastery_weight/etc.
        directly on each ``topics`` entry — the topic itself is the atomic
        study unit (a leaf: no nested children). DSA and LLD additionally
        break some topics down further into an explicit ``learning_nodes``
        container for finer-grained pattern-level tracking. Either shape is
        an equally valid "learning node" — the leaf granularity decides,
        never the track — so every track exposes identical Open KB / AI
        Mentor / Progress / Revision capability through this single API.

        RC1.3.5B · Adaptive-visibility fix: a ``subtopics`` container (e.g.
        an authored HashMap/SOLID/case-study sub-breakdown) that itself has
        no further children is stamped with the exact same metadata shape as
        a leaf ``topic`` (difficulty/prerequisites/company_importance/
        mastery_weight/etc — see ``_stamp_defaults`` in
        ``scripts/generate_roadmap.py``). It was previously excluded purely
        because of the JSON key name used to author it (``subtopics`` vs
        ``topics``), which silently hid hundreds of real, fully-metadata'd
        concepts (e.g. every HashMap internals sub-topic, every SOLID
        principle, every HLD/LLD case-study section) from the planner,
        ranking, unlock and ROI graphs. Recognizing it here is purely
        additive — every id previously returned by ``get_learning_nodes()``
        is still returned; this only adds more.
        """
        if node.get("type") == "node":
            return True
        return node.get("type") in ("topic", "subtopic") and not node.get("child_ids")

    def get_learning_nodes(self) -> List[dict]:
        """Return every atomic learning unit in roadmap order (see ``_is_learning_node``)."""
        return [node for node in self._index.values() if self._is_learning_node(node)]

    def get_learning_node(self, node_id: str) -> Optional[dict]:
        """Return one explicit learning node, excluding structural nodes."""
        node = self.get(node_id)
        return node if node and self._is_learning_node(node) else None

    def get_track_learning_nodes(self, track: str) -> List[dict]:
        """Return explicit learning nodes that belong to ``track``."""
        return [node for node in self.get_learning_nodes() if node.get("track") == track]

    def is_unlocked(self, node_id: str, completed_nodes: Iterable[str] = ()) -> bool:
        """Return whether all roadmap prerequisites for a learning node are complete."""
        node = self.get_learning_node(node_id)
        if not node:
            return False
        completed = set(completed_nodes)
        return all(prerequisite in completed for prerequisite in node.get("prerequisites", []))

    def get_unlocked_nodes(self, completed_nodes: Iterable[str]) -> List[dict]:
        """Return learning nodes whose roadmap prerequisites are complete."""
        completed = set(completed_nodes)
        return [
            node for node in self.get_learning_nodes()
            if self.is_unlocked(node["id"], completed)
        ]

    def get_next_learning_node(self, current_node: str) -> Optional[dict]:
        """Return the next explicit learning node in canonical roadmap order."""
        nodes = self.get_learning_nodes()
        for index, node in enumerate(nodes):
            if node["id"] == current_node:
                return nodes[index + 1] if index + 1 < len(nodes) else None
        return None


# Singleton
@lru_cache(maxsize=1)
def get_roadmap(version: str = CURRENT_VERSION) -> RoadmapEngine:
    return RoadmapEngine(version)


# ---------- Learning-node convenience APIs ----------
def get_learning_nodes(version: str = CURRENT_VERSION) -> List[dict]:
    """Return all explicit learning nodes for a roadmap version."""
    return get_roadmap(version).get_learning_nodes()


def get_learning_node(node_id: str, version: str = CURRENT_VERSION) -> Optional[dict]:
    """Return one explicit learning node for a roadmap version."""
    return get_roadmap(version).get_learning_node(node_id)


def get_track_learning_nodes(track: str, version: str = CURRENT_VERSION) -> List[dict]:
    """Return explicit learning nodes for a track."""
    return get_roadmap(version).get_track_learning_nodes(track)


def get_unlocked_nodes(
    completed_nodes: Iterable[str], version: str = CURRENT_VERSION,
) -> List[dict]:
    """Return learning nodes with all roadmap prerequisites completed."""
    return get_roadmap(version).get_unlocked_nodes(completed_nodes)


def is_unlocked(
    node_id: str, completed_nodes: Iterable[str] = (), version: str = CURRENT_VERSION,
) -> bool:
    """Return whether a learning node's roadmap prerequisites are completed."""
    return get_roadmap(version).is_unlocked(node_id, completed_nodes)


def get_next_learning_node(
    current_node: str, version: str = CURRENT_VERSION,
) -> Optional[dict]:
    """Return the next explicit learning node in canonical roadmap order."""
    return get_roadmap(version).get_next_learning_node(current_node)


# ---------- Adapters for backwards compatibility ----------
# The mission engine and other modules used to define TOPIC_META, PATTERN_TO_DOMAIN
# and pattern prerequisites inline. Expose the same shapes derived from roadmap.

def topic_meta() -> Dict[str, Dict]:
    """Return dict shaped like the legacy TOPIC_META: track_id → {label, subtopics: [(name, difficulty)]}"""
    r = get_roadmap()
    result: Dict[str, Dict] = {}
    for track in r.tracks():
        subs = []
        for module in track.get("modules", []) or []:
            for topic in module.get("topics", []) or []:
                subs.append((topic["label"], topic.get("difficulty", "medium")))
        result[track["id"]] = {"label": track["label"], "subtopics": subs}
    return result


def subtopic_to_pattern() -> Dict[str, str]:
    """Legacy SUBTOPIC_TO_PATTERN — label → pattern."""
    r = get_roadmap()
    result: Dict[str, str] = {}
    for n in r.all_nodes():
        pat = n.get("pattern")
        if pat and n.get("type") == "topic":
            result[n["label"]] = pat
    return result


def pattern_to_track() -> Dict[str, str]:
    """pattern → (track_id, track_label) — legacy PATTERN_TO_DOMAIN."""
    r = get_roadmap()
    result = {}
    for pat, nodes in r._by_pattern.items():
        node = nodes[0]
        track = r.find_track(node["id"])
        result[pat] = (track["id"] if track else "dsa", node["label"])
    return result


def pattern_for_node(node_id: str, version: str = CURRENT_VERSION) -> Optional[str]:
    """Return the interview pattern for a learning node (see `RoadmapEngine.pattern_for_node`)."""
    return get_roadmap(version).pattern_for_node(node_id)
