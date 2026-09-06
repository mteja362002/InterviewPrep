import os
import sys
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from services.learning_engine.planner import get_today_learning_node
from services.learning_engine.ranking import score_learning_node
from services.learning_engine.context import build_learner_context
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

# To flip: DSA needs ~13 more points from non-mastery-weight signals to offset 
# mastery_weight advantage of DBMS. Company swings 6, effective_knowledge_gap and
# subject_transition_bonus depend on the GAP. If DSA gap > DBMS gap, DSA gets
# more from those signals.
# Try: DSA=2 (gap=80), DBMS=5 (gap=50).
# effective_knowledge_gap contribution: (80-50)*0.6 = +18 for DSA
# subject_transition_bonus: (0.8-0.5)*100 = +30 for DSA
# This should overwhelm the 19-pt mastery_weight advantage of DBMS.
base = {
    "current_position": "1-3",
    "self_assessment": {
        "programming_fundamentals": 10, "java": 10,
        "dsa": 2, "dbms": 5, "operating_systems": 3,
        "computer_networks": 3, "lld": 4, "hld": 4,
    },
}

print("=== DSA=2, DBMS=5 (DSA has bigger gap) ===")
dsa_node = next((n for n in roadmap.get_learning_nodes() if n.get("track") == "dsa"), None)
dbms_node = next((n for n in roadmap.get_learning_nodes() if n.get("track") == "dbms"), None)

for company in ("google", "oracle"):
    onboarding = {**base, "target_companies": [company]}
    ctx = build_learner_context(onboarding=onboarding)
    dsa_s = score_learning_node(dsa_node, {}, target_companies=[company], learner_context=ctx)
    dbms_s = score_learning_node(dbms_node, {}, target_companies=[company], learner_context=ctx)
    print(f"  {company.upper()}: DSA={dsa_s['total_score']:.1f}, DBMS={dbms_s['total_score']:.1f}")
    pick = asyncio.run(get_today_learning_node("user", db=FakeDB([]), onboarding=onboarding))
    if pick:
        print(f"    PLANNER PICK: {pick['track']}")
