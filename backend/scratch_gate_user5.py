"""VERIFICATION GATE item 2 — User 5 runtime capture against the REAL database.

Unlike scratch_diagnose_user5.py (which uses a synthetic profile and a FakeDB),
this reads the actual `users` / `onboarding` / `knowledge_nodes` rows for
teja.2019.ece@anits.edu.in and runs the real planner pipeline over them, so the
numbers reported are runtime evidence rather than a simulation.

Reproduces the production read path used by routes_missions._generate_today_mission:
    onboarding          <- db.onboarding.find_one({"user_id": ...})
    knowledge_node_rows <- load_user_progress_rows(db, user_id)
    planner_progress_rows(roadmap, rows, onboarding)

Emits test_reports/gate_user5.json and prints a human-readable summary.
Read-only: performs no writes of any kind.

Run:  python scratch_gate_user5.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from roadmap import get_roadmap
from services.progress_engine import planner_progress_rows, load_user_progress_rows
from services.learning_engine.context import (
    build_learner_context, EFFECTIVE_SUBJECT_COMPLETE_THRESHOLD,
)
from services.learning_engine.stage_engine import compute_all_subject_states
from services.learning_engine.eligibility import eligible_learning_nodes
from services.learning_engine.subject_progression import (
    build_all_sessions, build_daily_learning_plan,
)
from services.learning_engine.planner import get_today_learning_node

TARGET_EMAIL = "teja.2019.ece@anits.edu.in"

# The gate's definition of "advanced technical".
ADVANCED_TRACKS = {"dsa", "java", "lld", "hld",
                   "operating_systems", "dbms", "computer_networks"}
# Tracks the gate asks us to confirm still yield candidates.
GATE_TRACKS = ["dsa", "lld", "hld", "operating_systems", "dbms", "computer_networks"]

BEGINNER = {
    "current_position": "0-1",
    "daily_study_hours": 2,
    "target_companies": ["tcs"],
    "self_assessment": {
        "programming_fundamentals": 2, "java": 1, "dsa": 1,
        "operating_systems": 1, "dbms": 1, "computer_networks": 1,
        "lld": 0, "hld": 0, "projects": 0, "resume": 0, "behavioral": 0,
    },
}


def _plan_rows(plan):
    return [
        {
            "track": tp.session.track_id,
            "node_id": tp.node_id,
            "reason_code": tp.reason_code,
            "explanation": getattr(tp, "explanation", None),
        }
        for tp in plan.task_plans
    ]


async def main():
    load_dotenv()
    mongo_url = os.environ["MONGO_URL"]
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ["DB_NAME"]]

    out: dict = {"target_email": TARGET_EMAIL}
    roadmap = get_roadmap()

    # ---- Resolve the real user -------------------------------------
    user = await db.users.find_one({"email": TARGET_EMAIL}, {"_id": 0})
    if not user:
        print(f"FATAL: no user row for {TARGET_EMAIL}")
        print("Users present:")
        async for u in db.users.find({}, {"_id": 0, "email": 1}):
            print("   ", u.get("email"))
        sys.exit(2)
    user_id = user["id"]
    out["user_id"] = user_id
    out["onboarding_completed"] = user.get("onboarding_completed")

    onboarding = await db.onboarding.find_one({"user_id": user_id}, {"_id": 0})
    if not onboarding:
        print(f"FATAL: user {user_id} has no onboarding row.")
        sys.exit(2)
    out["self_assessment"] = onboarding.get("self_assessment", {})
    out["target_companies"] = onboarding.get("target_companies", [])
    out["daily_study_hours"] = onboarding.get("daily_study_hours")
    out["current_position"] = onboarding.get("current_position")
    out["interview_target_date"] = onboarding.get("interview_target_date")

    # ---- Real stored progress --------------------------------------
    stored = await load_user_progress_rows(db, user_id)
    raw_rows = list(stored.values())
    out["stored_progress_rows"] = len(raw_rows)

    # Provenance census of what is actually in the DB for this user.
    census: dict = {}
    for r in raw_rows:
        census[r.get("planner_progress_source") or "<unset>"] = \
            census.get(r.get("planner_progress_source") or "<unset>", 0) + 1
    out["stored_provenance_census"] = census

    progress_rows = planner_progress_rows(roadmap, raw_rows, onboarding)
    context = build_learner_context(
        onboarding=onboarding,
        progress_rows=progress_rows,
        target_companies=onboarding.get("target_companies") or [],
    )

    # Post-derivation census (what the planner actually sees).
    derived: dict = {}
    for r in progress_rows:
        derived[r.get("planner_progress_source") or "<unset>"] = \
            derived.get(r.get("planner_progress_source") or "<unset>", 0) + 1
    out["derived_provenance_census"] = derived

    # ---- Effective knowledge / effectively-completed ----------------
    out["effective_threshold"] = EFFECTIVE_SUBJECT_COMPLETE_THRESHOLD
    out["effective_scores"] = {
        tid: round(context.effective_knowledge_score(tid), 2)
        for tid in roadmap.track_ids()
    }
    out["evidence_weight_alpha"] = {
        tid: round(context.mastery_evidence_weight(tid), 3)
        for tid in roadmap.track_ids()
    }
    out["effectively_completed_tracks"] = list(context.effectively_completed_tracks())
    out["effective_completed_subject_ids"] = list(
        context.effective_completed_subject_ids(roadmap))

    # ---- Subject states --------------------------------------------
    subject_states = compute_all_subject_states(roadmap, context.progress_map)
    out["subject_states"] = {
        tid: {
            "current_stage": s.current_stage,
            "completed_stage": s.completed_stage,
            "next_eligible_stage": s.next_eligible_stage,
            "confidence": s.current_confidence,
        }
        for tid, s in subject_states.items()
    }

    # ---- Eligible candidate pool -----------------------------------
    eligible = eligible_learning_nodes(
        context.progress_map, subject_states,
        urgency=context.urgency,
        virtual_completed_node_ids=context.virtual_completed_node_ids(),
    )
    out["eligible_candidate_count"] = len(eligible)

    by_track: dict = {}
    for n in eligible:
        t = n.get("track", "unknown")
        st = n.get("learning_stage", "foundation")
        by_track.setdefault(t, {})
        by_track[t][st] = by_track[t].get(st, 0) + 1
    out["eligible_by_track_stage"] = by_track
    out["eligible_by_track"] = {t: sum(v.values()) for t, v in by_track.items()}

    advanced = [n for n in eligible if n.get("track") in ADVANCED_TRACKS]
    out["advanced_technical_candidate_count"] = len(advanced)

    # Gate: DSA / LLD / HLD / Core CS candidates must be available.
    out["gate_track_availability"] = {
        t: out["eligible_by_track"].get(t, 0) for t in GATE_TRACKS
    }

    # ---- Session pipeline ------------------------------------------
    sessions = build_all_sessions(
        roadmap, context.progress_map,
        effective_completed_subjects=context.effective_completed_subject_ids(roadmap),
    )
    out["sessions"] = {
        tid: {"status": s.status, "next_node_id": s.next_node_id,
              "topic_lifecycle": s.topic_lifecycle}
        for tid, s in sessions.items()
    }
    status_counts: dict = {}
    for s in sessions.values():
        status_counts[s.status] = status_counts.get(s.status, 0) + 1
    out["session_status_counts"] = status_counts

    # ---- Daily plan (the actual selection) -------------------------
    plan = build_daily_learning_plan(sessions, roadmap)
    out["selected_task_plans"] = _plan_rows(plan)
    out["selected_tracks"] = sorted({r["track"] for r in out["selected_task_plans"]})
    out["reason_codes"] = [r["reason_code"] for r in out["selected_task_plans"]]
    total = len(out["selected_task_plans"])
    behavioral = sum(1 for r in out["selected_task_plans"] if r["track"] == "behavioral")
    out["behavioral_selected"] = behavioral
    out["total_selected"] = total

    # ---- Full planner pick (end to end, real db) -------------------
    pick = await get_today_learning_node(
        user_id, db=db, onboarding=onboarding,
        target_companies=onboarding.get("target_companies") or [],
        knowledge_rows=await _knowledge_rows(db, user_id),
    )
    out["planner_pick"] = {
        "track": (pick or {}).get("track"),
        "node_id": (pick or {}).get("node_id"),
        "label": (pick or {}).get("label"),
        "difficulty": (pick or {}).get("difficulty"),
    } if pick else None

    # ---- Beginner regression (synthetic control) -------------------
    b_rows = planner_progress_rows(roadmap, [], BEGINNER)
    b_ctx = build_learner_context(onboarding=BEGINNER, progress_rows=b_rows,
                                 target_companies=BEGINNER["target_companies"])
    b_sessions = build_all_sessions(
        roadmap, b_ctx.progress_map,
        effective_completed_subjects=b_ctx.effective_completed_subject_ids(roadmap))
    b_plan = build_daily_learning_plan(b_sessions, roadmap)
    out["beginner_control"] = {
        "task_plans": _plan_rows(b_plan),
        "tracks": sorted({tp.session.track_id for tp in b_plan.task_plans}),
        "got_advanced_lld_hld": sorted(
            {tp.session.track_id for tp in b_plan.task_plans
             if tp.session.track_id in ("lld", "hld")}),
    }

    # ---- Gate assertions -------------------------------------------
    checks = {
        "structured_session_pipeline_non_empty": total > 0,
        "advanced_technical_candidates_available":
            out["advanced_technical_candidate_count"] > 0,
        "behavioral_not_sole_fallback": not (total > 0 and behavioral == total),
        "dsa_candidates_available": out["gate_track_availability"].get("dsa", 0) > 0,
        "lld_candidates_available": out["gate_track_availability"].get("lld", 0) > 0,
        "hld_candidates_available": out["gate_track_availability"].get("hld", 0) > 0,
        "core_cs_candidates_available": all(
            out["gate_track_availability"].get(t, 0) > 0
            for t in ("operating_systems", "dbms", "computer_networks")),
        "beginner_no_advanced_regression":
            not out["beginner_control"]["got_advanced_lld_hld"],
        "beginner_plan_non_empty": len(out["beginner_control"]["task_plans"]) > 0,
        "planner_returned_a_recommendation": pick is not None,
    }
    out["checks"] = checks
    out["all_checks_passed"] = all(checks.values())

    # ---- Write + summarise -----------------------------------------
    dest = Path(__file__).parent / "test_reports" / "gate_user5.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")

    print("=" * 72)
    print(f"USER 5 RUNTIME CAPTURE — {TARGET_EMAIL}")
    print("=" * 72)
    print(f"  user_id                        : {user_id}")
    print(f"  stored progress rows           : {out['stored_progress_rows']}")
    print(f"  stored provenance census       : {census}")
    print(f"  derived provenance census      : {derived}")
    print(f"  effectively completed tracks   : {out['effectively_completed_tracks']}")
    print(f"  ELIGIBLE CANDIDATE COUNT       : {out['eligible_candidate_count']}")
    print(f"  ADVANCED TECHNICAL CANDIDATES  : {out['advanced_technical_candidate_count']}")
    print(f"  per-gate-track availability    : {out['gate_track_availability']}")
    print(f"  session status counts          : {status_counts}")
    print(f"  SELECTED TASK PLANS            : {total}  (behavioral {behavioral}/{total})")
    for r in out["selected_task_plans"]:
        print(f"      - {r['track']:<20} {r['node_id']:<38} reason={r['reason_code']}")
    print(f"  selected tracks                : {out['selected_tracks']}")
    print(f"  planner pick                   : {out['planner_pick']}")
    print(f"  beginner control tracks        : {out['beginner_control']['tracks']}")
    print()
    print("  CHECKS")
    for k, v in checks.items():
        print(f"    [{'PASS' if v else 'FAIL'}] {k}")
    print()
    print(f"  RESULT: {'ALL CHECKS PASSED' if out['all_checks_passed'] else 'FAILURES PRESENT'}")
    print(f"  JSON  : {dest}")
    client.close()


async def _knowledge_rows(db, user_id):
    """Mirror routes_missions._get_knowledge minimally (per-track scores)."""
    from routes_missions import _get_knowledge
    try:
        return await _get_knowledge(db, user_id)
    except Exception:
        return None


if __name__ == "__main__":
    asyncio.run(main())
