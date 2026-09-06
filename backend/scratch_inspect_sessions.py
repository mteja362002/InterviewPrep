import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from services.learning_engine.context import build_learner_context
from services.learning_engine.subject_progression import build_all_sessions, build_daily_learning_plan
from roadmap import get_roadmap

roadmap = get_roadmap()

base = {
    "current_position": "1-3",
    "self_assessment": {
        "programming_fundamentals": 10, "java": 10,
        "dsa": 3, "dbms": 4, "operating_systems": 8,
        "computer_networks": 8, "lld": 4, "hld": 4,
    },
    "target_companies": ["oracle"],
}

ctx = build_learner_context(onboarding=base)
effective = ctx.effective_completed_subject_ids(roadmap)
print(f"Effective completed: {effective}")

sessions = build_all_sessions(roadmap, ctx.progress_map, effective_completed_subjects=effective)
print("\nAll sessions:")
for tid, s in sessions.items():
    print(f"  {tid}: status={s.status}, next_node={s.next_node_id}")

plan = build_daily_learning_plan(sessions, roadmap, recent_track_ids=[])
print(f"\nTask plans ({len(plan.task_plans)}):")
for i, tp in enumerate(plan.task_plans):
    print(f"  [{i}] {tp.session.track_id}: node={tp.node_id}, reason={tp.reason_code}")
