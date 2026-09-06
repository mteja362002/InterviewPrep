import os
import sys
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from services.learning_engine.context import build_learner_context
from services.learning_engine.priority_engine import score_candidate
from services.learning_engine.subject_progression import build_all_sessions, build_daily_learning_plan
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

# DSA=3, DBMS=4. OS/CN at 6 (below 7 threshold, so not effectively completed)
# LLD/HLD high so they're effectively completed but they're locked anyway
base = {
    "current_position": "1-3",
    "self_assessment": {
        "programming_fundamentals": 10, "java": 10,
        "dsa": 3, "dbms": 4, "operating_systems": 6,
        "computer_networks": 6, "lld": 4, "hld": 4,
    },
}

for company in ("google", "oracle"):
    onboarding = {**base, "target_companies": [company]}
    ctx = build_learner_context(onboarding=onboarding)
    eff = ctx.effective_completed_subject_ids(roadmap)
    
    print(f"\n{company.upper()} (effective: {eff})")
    
    sessions = build_all_sessions(roadmap, ctx.progress_map, effective_completed_subjects=eff)
    plan = build_daily_learning_plan(sessions, roadmap, recent_track_ids=[])
    
    print("  Task plans:")
    for tp in plan.task_plans:
        node = roadmap.get(tp.node_id)
        if node:
            p = score_candidate(node, ctx)
            print(f"    {tp.session.track_id}: score={p.score:.1f}, node={tp.node_id}")
    
    pick = asyncio.run(get_today_learning_node("user", db=FakeDB([]), onboarding=onboarding))
    if pick:
        print(f"  PLANNER PICK: {pick['track']}")
