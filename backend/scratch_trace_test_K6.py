import os
import sys
import asyncio

# Add backend to path so we can import modules
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

onboarding_g = {**base_onboarding, "target_companies": ["google"]}
onboarding_o = {**base_onboarding, "target_companies": ["oracle"]}

pick_g = asyncio.run(get_today_learning_node("user", db=FakeDB([]), onboarding=onboarding_g))
pick_o = asyncio.run(get_today_learning_node("user", db=FakeDB([]), onboarding=onboarding_o))

if pick_g:
    print(f"GOOGLE PICK: {pick_g['node_id']} (track: {pick_g['track']})")
else:
    print("GOOGLE PICK: None")
if pick_o:
    print(f"ORACLE PICK: {pick_o['node_id']} (track: {pick_o['track']})")
else:
    print("ORACLE PICK: None")
