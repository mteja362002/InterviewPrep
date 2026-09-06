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

dsa_node = next((n for n in roadmap.get_learning_nodes() if n.get("track") == "dsa"), None)
dbms_node = next((n for n in roadmap.get_learning_nodes() if n.get("track") == "dbms"), None)

# Sweep: DSA gap slightly bigger to offset mastery_weight, within company flip range
for dsa_val, dbms_val in [(3, 4), (4, 5), (2, 4), (3, 5), (4, 6), (5, 6), (5, 7), (4, 7)]:
    base = {
        "current_position": "1-3",
        "self_assessment": {
            "programming_fundamentals": 10, "java": 10,
            "dsa": dsa_val, "dbms": dbms_val, "operating_systems": 3,
            "computer_networks": 3, "lld": 4, "hld": 4,
        },
    }
    print(f"\nDSA={dsa_val}, DBMS={dbms_val}:")
    results = {}
    for company in ("google", "oracle"):
        onboarding = {**base, "target_companies": [company]}
        ctx = build_learner_context(onboarding=onboarding)
        dsa_s = score_learning_node(dsa_node, {}, target_companies=[company], learner_context=ctx)["total_score"]
        dbms_s = score_learning_node(dbms_node, {}, target_companies=[company], learner_context=ctx)["total_score"]
        winner = "dsa" if dsa_s > dbms_s else "dbms"
        results[company] = winner
        print(f"  {company.upper()}: DSA={dsa_s:.1f}, DBMS={dbms_s:.1f} => {winner}")
    if results["google"] != results["oracle"]:
        print("  *** COMPANY FLIP FOUND ***")
        # Also verify planner agrees
        for company in ("google", "oracle"):
            onboarding = {**base, "target_companies": [company]}
            pick = asyncio.run(get_today_learning_node("user", db=FakeDB([]), onboarding=onboarding))
            if pick:
                print(f"  PLANNER {company.upper()}: {pick['track']}")
