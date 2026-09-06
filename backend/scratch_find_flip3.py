import os
import sys
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from services.learning_engine.ranking import score_learning_node
from services.learning_engine.context import build_learner_context
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

# DSA=3, DBMS=4, OS/CN high enough to not compete
base = {
    "current_position": "1-3",
    "self_assessment": {
        "programming_fundamentals": 10, "java": 10,
        "dsa": 3, "dbms": 4, "operating_systems": 8,
        "computer_networks": 8, "lld": 4, "hld": 4,
    },
}

dsa_node = next((n for n in roadmap.get_learning_nodes() if n.get("track") == "dsa"), None)
dbms_node = next((n for n in roadmap.get_learning_nodes() if n.get("track") == "dbms"), None)
os_node = next((n for n in roadmap.get_learning_nodes() if n.get("track") == "operating_systems"), None)

for company in ("google", "oracle"):
    onboarding = {**base, "target_companies": [company]}
    ctx = build_learner_context(onboarding=onboarding)
    dsa_s = score_learning_node(dsa_node, {}, target_companies=[company], learner_context=ctx)["total_score"]
    dbms_s = score_learning_node(dbms_node, {}, target_companies=[company], learner_context=ctx)["total_score"]
    os_s = score_learning_node(os_node, {}, target_companies=[company], learner_context=ctx)["total_score"]
    print(f"{company.upper()}: DSA={dsa_s:.1f}, DBMS={dbms_s:.1f}, OS={os_s:.1f}")
    pick = asyncio.run(get_today_learning_node("user", db=FakeDB([]), onboarding=onboarding))
    if pick:
        print(f"  PLANNER: {pick['track']}")
