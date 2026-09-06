import os
import sys
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from services.learning_engine.context import build_learner_context
from services.learning_engine.priority_engine import score_candidate
from services.learning_engine.planner import get_today_learning_node
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

# The task plans are: dsa, dbms, projects
# Score just these three nodes
base = {
    "current_position": "1-3",
    "self_assessment": {
        "programming_fundamentals": 10, "java": 10,
        "dsa": 3, "dbms": 4, "operating_systems": 8,
        "computer_networks": 8, "lld": 4, "hld": 4,
    },
}

for company in ("google", "oracle"):
    onboarding = {**base, "target_companies": [company]}
    ctx = build_learner_context(onboarding=onboarding)
    
    print(f"\n{company.upper()} - Scoring task plan candidates:")
    for node_id in ["dsa.foundations.arrays.traversal", "dbms.relational.keys", "projects.build.url_shortener"]:
        node = roadmap.get(node_id)
        if node:
            p = score_candidate(node, ctx)
            print(f"  {node.get('track')}: {p.score:.1f}")
    
    pick = asyncio.run(get_today_learning_node("user", db=FakeDB([]), onboarding=onboarding))
    if pick:
        print(f"  PLANNER PICK: {pick['track']}")
