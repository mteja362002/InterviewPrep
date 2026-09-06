import os
import sys
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from services.learning_engine.ranking import score_learning_node
from services.learning_engine.context import build_learner_context
from services.learning_engine.planner import get_today_learning_node
from services.learning_engine.priority_engine import score_candidate
from roadmap import get_roadmap

roadmap = get_roadmap()

class FakeCursor:
    def __init__(self, rows):
        self._rows = rows
    async def to_list(self, length=None):
        return list(self._rows)

class FakeCollection:
    def __init__(self, rows):
        self._rows = rows
    def find(self, query=None, projection=None):
        return FakeCursor(list(self._rows))

class FakeDB:
    def __init__(self, rows):
        self.knowledge_nodes = FakeCollection(rows)

base = {
    "current_position": "1-3",
    "self_assessment": {
        "programming_fundamentals": 10, "java": 10,
        "dsa": 3, "dbms": 4, "operating_systems": 8,
        "computer_networks": 8, "lld": 4, "hld": 4,
    },
}

# Score ALL first learning nodes across all tracks
ctx = build_learner_context(onboarding={**base, "target_companies": ["oracle"]})
print("ALL track first-node scores (Oracle):")
for track_id in roadmap.track_ids():
    nodes = roadmap.get_track_learning_nodes(track_id)
    if nodes:
        node = nodes[0]
        p = score_candidate(node, ctx)
        print(f"  {track_id}: {p.score:.1f} ({node['id']})")
