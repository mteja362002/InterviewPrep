import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from services.learning_engine.context import build_learner_context
from services.learning_engine.priority_engine import score_candidate
from services.learning_engine.subject_progression import build_all_sessions, build_daily_learning_plan
from roadmap import get_roadmap
import json

roadmap = get_roadmap()

# Test A3 state: PF=10 (effectively complete), Java=1 
onboarding = {
    "current_position": "student",
    "target_companies": ["google"],
    "self_assessment": {
        "programming_fundamentals": 10, "java": 1,
        "dsa": 0, "dbms": 0, "operating_systems": 0,
        "computer_networks": 0, "lld": 0, "hld": 0,
    },
}
ctx = build_learner_context(onboarding=onboarding, target_companies=["google"])

for node_id in ["java.basics.programming_intro", "behavioral.framework.star"]:
    node = roadmap.get(node_id)
    if node:
        p = score_candidate(node, ctx)
        print(f"\n{node.get('track')} ({node_id}):")
        print(f"  Score: {p.score:.1f}")
        print(f"  Breakdown: {json.dumps(p.breakdown, indent=2)}")
