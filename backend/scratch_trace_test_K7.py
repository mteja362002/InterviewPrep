import os
import sys
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from services.learning_engine.planner import get_today_learning_node
from roadmap import get_roadmap

roadmap = get_roadmap()

base_onboarding = {
    "current_position": "1-3",
    "self_assessment": {
        "programming_fundamentals": 10, "java": 10,
        "dsa": 2, "dbms": 3, "operating_systems": 3,
        "computer_networks": 3, "lld": 4, "hld": 4,
    },
}

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

onboarding_o = {**base_onboarding, "target_companies": ["oracle"]}

# Let's inspect the planner logic manually to see why it rejected DBMS
from services.learning_engine.context import build_learner_context
from services.learning_engine.stage_engine import compute_all_subject_states
from services.learning_engine.eligibility import eligible_learning_nodes
from services.learning_engine.ranking import rank_learning_nodes

ctx = build_learner_context(onboarding=onboarding_o)
virtual = ctx.virtual_completed_node_ids()
effective = ctx.effective_completed_subject_ids(roadmap)
states = compute_all_subject_states(roadmap, {})

eligible = eligible_learning_nodes({}, states, virtual_completed_node_ids=virtual)
ranked = rank_learning_nodes(eligible, {}, target_companies=["oracle"], learner_context=ctx)

for r in ranked[:10]:
    print(f"{r['id']} ({r.get('track')}): {r.get('score')}")
