import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from services.learning_engine.context import build_learner_context
from services.learning_engine.priority_engine import score_candidate
from services.learning_engine.subject_progression import build_all_sessions, build_daily_learning_plan
from roadmap import get_roadmap

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
eff = ctx.effective_completed_subject_ids(roadmap)
print(f"Effective: {eff}")

sessions = build_all_sessions(roadmap, ctx.progress_map, effective_completed_subjects=eff)
plan = build_daily_learning_plan(sessions, roadmap, recent_track_ids=[])

print(f"\nTask plans ({len(plan.task_plans)}):")
for tp in plan.task_plans:
    node = roadmap.get(tp.node_id)
    if node:
        p = score_candidate(node, ctx)
        print(f"  {tp.session.track_id}: score={p.score:.1f}, node={tp.node_id}, reason={tp.reason_code}")
