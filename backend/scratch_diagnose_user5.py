"""Diagnostic: trace the planner pipeline for User 5 (interview-ready) profile."""
import asyncio
import sys
sys.path.insert(0, ".")

from roadmap import get_roadmap
from services.learning_engine.planner import get_today_learning_node
from services.learning_engine.context import build_learner_context, EFFECTIVE_SUBJECT_COMPLETE_THRESHOLD
from services.learning_engine.stage_engine import compute_all_subject_states
from services.learning_engine.eligibility import eligible_learning_nodes
from services.learning_engine.subject_progression import build_all_sessions, build_daily_learning_plan
from services.learning_engine.candidates import generate_candidate_nodes
from services.learning_engine.priority_engine import score_candidates
from services.progress_engine import planner_progress_rows

class FakeCollection:
    def __init__(self, rows):
        self.rows = rows
    def find(self, *a, **kw):
        return FakeCursor(self.rows)

class FakeDB:
    def __init__(self, rows):
        self.rows = rows
        self.knowledge_nodes = FakeCollection(rows)

class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
    def sort(self, *a, **kw):
        return self
    async def to_list(self, *a, **kw):
        return self.rows

# User 5 profile
ONBOARDING = {
    "current_position": "3-5",  # 3 years experience
    "daily_study_hours": 5,
    "target_companies": ["google", "meta", "uber", "microsoft"],
    "interview_target_date": None,
    "preferred_language": "Java",
    "self_assessment": {
        "programming_fundamentals": 10,
        "java": 10,
        "dsa": 9,
        "operating_systems": 9,
        "dbms": 9,
        "computer_networks": 9,
        "lld": 8,
        "hld": 6,
        "projects": 9,
        "resume": 9,
        "behavioral": 9,
    }
}

def main():
    roadmap = get_roadmap()

    # 1. Show all tracks in the roadmap
    print("=" * 80)
    print("1. ROADMAP TRACKS")
    print("=" * 80)
    for tid in roadmap.track_ids():
        track = roadmap.get(tid)
        nodes = roadmap.get_track_learning_nodes(tid)
        prereqs = (track or {}).get("subject_prerequisites", [])
        print(f"  {tid}: {len(nodes)} nodes, prereqs={prereqs}")

    # 2. Build context and check effective knowledge for each track
    print("\n" + "=" * 80)
    print("2. EFFECTIVE KNOWLEDGE SCORES (User 5)")
    print("=" * 80)
    raw_rows = []  # No actual progress
    progress_rows_list = planner_progress_rows(roadmap, raw_rows, ONBOARDING)
    progress_map = {row["node_id"]: row for row in progress_rows_list if row.get("node_id")}
    
    context = build_learner_context(
        onboarding=ONBOARDING,
        progress_rows=progress_rows_list,
        target_companies=ONBOARDING["target_companies"],
    )

    for tid in roadmap.track_ids():
        eff = context.effective_knowledge_score(tid)
        alpha = context.mastery_evidence_weight(tid)
        self_score = context.onboarding_scores.get(tid, "N/A")
        print(f"  {tid}: eff={eff:.1f}, alpha={alpha:.2f}, self_assessment={self_score}")

    # 3. Check effectively completed tracks
    print("\n" + "=" * 80)
    print(f"3. EFFECTIVELY COMPLETED TRACKS (threshold={EFFECTIVE_SUBJECT_COMPLETE_THRESHOLD})")
    print("=" * 80)
    eff_tracks = context.effectively_completed_tracks()
    print(f"  {eff_tracks}")

    effective_subjects = context.effective_completed_subject_ids(roadmap)
    print(f"  effective_completed_subject_ids: {effective_subjects}")

    # 4. Subject states
    print("\n" + "=" * 80)
    print("4. SUBJECT LEARNING STATES")
    print("=" * 80)
    subject_states = compute_all_subject_states(roadmap, context.progress_map)
    for tid, state in subject_states.items():
        print(f"  {tid}: stage={state.current_stage}, completed={state.completed_stage}, "
              f"next_eligible={state.next_eligible_stage}, confidence={state.current_confidence}")

    # 5. Eligible nodes (with stage breakdown)
    print("\n" + "=" * 80)
    print("5. ELIGIBLE NODES (stage-level breakdown)")
    print("=" * 80)
    virtual_completed = context.virtual_completed_node_ids()
    eligible = eligible_learning_nodes(
        context.progress_map, subject_states,
        urgency=context.urgency,
        virtual_completed_node_ids=virtual_completed,
    )
    track_stage_map = {}
    for node in eligible:
        t = node.get("track", "unknown")
        stage = node.get("learning_stage", "foundation")
        track_stage_map.setdefault(t, {}).setdefault(stage, []).append(node["id"])
    print(f"  Total eligible: {len(eligible)}")
    for t in sorted(track_stage_map.keys()):
        stages = track_stage_map[t]
        total = sum(len(v) for v in stages.values())
        stage_summary = ", ".join(f"{s}={len(ids)}" for s, ids in sorted(stages.items()))
        print(f"    {t}: {total} nodes [{stage_summary}]")
    
    # Acceptance criterion: advanced technical candidates exist
    advanced_tracks = {"dsa", "java", "lld", "hld", "operating_systems", "dbms", "computer_networks"}
    advanced_eligible = [n for n in eligible if n.get("track") in advanced_tracks]
    print(f"\n  Advanced technical candidates: {len(advanced_eligible)}")
    print(f"  ✓ PASS" if len(advanced_eligible) > 0 else f"  ✗ FAIL")

    # 6. Session pipeline
    print("\n" + "=" * 80)
    print("6. SESSION PIPELINE (build_all_sessions)")
    print("=" * 80)
    sessions = build_all_sessions(
        roadmap, context.progress_map,
        effective_completed_subjects=context.effective_completed_subject_ids(roadmap),
    )
    active_count = 0
    completed_count = 0
    for tid, session in sessions.items():
        if session.status not in ("locked",):
            flag = ""
            if session.status == "active":
                active_count += 1
                flag = " ← ACTIVE (P4 eligible)"
            elif session.status == "completed":
                completed_count += 1
                flag = " ← completed (not serviced by P1-P5)"
            print(f"  {tid}: status={session.status}, next_node={session.next_node_id}, "
                  f"lifecycle={session.topic_lifecycle}{flag}")
    print(f"\n  Active sessions: {active_count}, Completed sessions: {completed_count}")
    print(f"  ✓ PASS (active sessions available)" if active_count > 0 
          else f"  ✗ FAIL (no active sessions)")

    # 7. Daily learning plan (what actually gets selected)
    print("\n" + "=" * 80)
    print("7. DAILY LEARNING PLAN (select_subjects_for_today)")
    print("=" * 80)
    plan = build_daily_learning_plan(sessions, roadmap)
    if plan.task_plans:
        for tp in plan.task_plans:
            print(f"  SELECTED: track={tp.session.track_id}, node={tp.node_id}, "
                  f"reason={tp.reason_code}, explanation={tp.explanation}")
        # Check no behavioral domination
        behavioral_count = sum(1 for tp in plan.task_plans if tp.session.track_id == "behavioral")
        total = len(plan.task_plans)
        print(f"\n  Behavioral tasks: {behavioral_count}/{total}")
        if behavioral_count > total // 2:
            print(f"  ⚠ WARNING: Behavioral dominates without deterministic justification")
        else:
            print(f"  ✓ PASS: Behavioral does not dominate")
    else:
        print("  ✗ FAIL: EMPTY plan — session pipeline produced zero task plans!")

    # 8. Score all session-pipeline candidates
    print("\n" + "=" * 80)
    print("8. SCORING SESSION CANDIDATES")
    print("=" * 80)
    for tp in plan.task_plans:
        node = roadmap.get(tp.node_id)
        if node:
            from services.learning_engine.priority_engine import score_candidate
            priority = score_candidate(node, context)
            bd = priority.breakdown
            print(f"  {tp.node_id} (track={node.get('track')})")
            print(f"    total_score={bd.get('total_score', 0):.2f}")
            print(f"    knowledge_gap={bd.get('knowledge_gap', 0):.2f}")
            print(f"    effective_gap={bd.get('effective_knowledge_gap', 0):.2f}")
            print(f"    company_score={bd.get('company_score', 0):.2f}")
            print(f"    foundation_bonus={bd.get('foundation_bonus', 0):.2f}")
            print(f"    prereq_gap_penalty={bd.get('prerequisite_gap_penalty', 0):.2f}")
            print(f"    subject_transition={bd.get('subject_transition_bonus', 0):.2f}")

    # 9. Full planner pick
    print("\n" + "=" * 80)
    print("9. FULL PLANNER PICK (User 5 — interview-ready)")
    print("=" * 80)
    pick = asyncio.run(get_today_learning_node(
        "user-5-diag", db=FakeDB([]), onboarding=ONBOARDING,
        target_companies=ONBOARDING["target_companies"],
    ))
    if pick:
        print(f"  track: {pick.get('track')}")
        print(f"  node_id: {pick.get('node_id')}")
        print(f"  label: {pick.get('label')}")
        print(f"  subtopic: {pick.get('subtopic')}")
        print(f"  difficulty: {pick.get('difficulty')}")
        insight = pick.get("insight", {})
        print(f"  insight.why: {insight.get('why_this_topic', 'N/A')}")
        if pick.get("track") in advanced_tracks:
            print(f"  ✓ PASS: Primary recommendation is advanced technical content")
        else:
            print(f"  ⚠ Primary recommendation is {pick.get('track')} (may be expected)")
    else:
        print("  ✗ FAIL: NO RECOMMENDATION!")

    # 10. Beginner profile regression test
    print("\n" + "=" * 80)
    print("10. BEGINNER PROFILE (regression check)")
    print("=" * 80)
    BEGINNER = {
        "current_position": "0-1",
        "daily_study_hours": 2,
        "target_companies": ["tcs"],
        "self_assessment": {
            "programming_fundamentals": 2,
            "java": 1,
            "dsa": 1,
            "operating_systems": 1,
            "dbms": 1,
            "computer_networks": 1,
            "lld": 0,
            "hld": 0,
            "projects": 0,
            "resume": 0,
            "behavioral": 0,
        }
    }
    beginner_rows = planner_progress_rows(roadmap, [], BEGINNER)
    beginner_ctx = build_learner_context(
        onboarding=BEGINNER, progress_rows=beginner_rows,
        target_companies=BEGINNER["target_companies"],
    )
    beginner_sessions = build_all_sessions(
        roadmap, beginner_ctx.progress_map,
        effective_completed_subjects=beginner_ctx.effective_completed_subject_ids(roadmap),
    )
    beginner_plan = build_daily_learning_plan(beginner_sessions, roadmap)
    if beginner_plan.task_plans:
        for tp in beginner_plan.task_plans:
            print(f"  SELECTED: track={tp.session.track_id}, node={tp.node_id}, reason={tp.reason_code}")
        # Beginner should NOT get advanced content
        beginner_advanced = [tp for tp in beginner_plan.task_plans 
                            if tp.session.track_id in ("lld", "hld")]
        if beginner_advanced:
            print(f"  ⚠ WARNING: Beginner got advanced track: {[t.session.track_id for t in beginner_advanced]}")
        else:
            print(f"  ✓ PASS: Beginner gets foundational content")
    else:
        print("  ⚠ WARNING: Beginner plan is empty")

if __name__ == "__main__":
    main()

