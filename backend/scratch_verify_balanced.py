import os
import sys
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from services.learning_engine.planner import get_today_learning_node
from services.learning_engine.ranking import score_learning_node
from services.learning_engine.context import build_learner_context
from roadmap import get_roadmap

roadmap = get_roadmap()

# BALANCED state: DSA=3, Core CS=3 - company signal can differentiate
base_onboarding = {
    "current_position": "1-3",
    "self_assessment": {
        "programming_fundamentals": 10, "java": 10,
        "dsa": 3, "dbms": 3, "operating_systems": 3,
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

print("=== BALANCED state (DSA=3, Core CS=3) ===")
for company in ("google", "oracle"):
    onboarding = {**base_onboarding, "target_companies": [company]}
    pick = asyncio.run(get_today_learning_node("user", db=FakeDB([]), onboarding=onboarding))
    if pick:
        print(f"  {company.upper()} PICK: {pick['node_id']} (track: {pick['track']})")

# Direct scores
print("\n=== Direct scores ===")
dsa_node = next((n for n in roadmap.get_learning_nodes() if n.get("track") == "dsa"), None)
dbms_node = next((n for n in roadmap.get_learning_nodes() if n.get("track") == "dbms"), None)
cn_node = next((n for n in roadmap.get_learning_nodes() if n.get("track") == "computer_networks"), None)
for company in ("google", "oracle"):
    ctx = build_learner_context(onboarding={**base_onboarding, "target_companies": [company]})
    dsa_s = score_learning_node(dsa_node, {}, target_companies=[company], learner_context=ctx)
    dbms_s = score_learning_node(dbms_node, {}, target_companies=[company], learner_context=ctx)
    cn_s = score_learning_node(cn_node, {}, target_companies=[company], learner_context=ctx)
    print(f"  {company.upper()}: DSA={dsa_s['total_score']:.1f}, DBMS={dbms_s['total_score']:.1f}, CN={cn_s['total_score']:.1f}")
