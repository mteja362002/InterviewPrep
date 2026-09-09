"""Read-only verification against existing profiles. Never calls write routes."""
import argparse
import asyncio
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from roadmap import get_roadmap
from services.evidence import certified_fields, legacy_fields, planner_row
from services.progress_engine import load_user_progress_rows, build_canonical_progress, planner_progress_rows, count_remaining_learning_nodes
from services.learning_engine.context import build_learner_context
from services.learning_engine.planner import get_today_learning_node
from services.learning_engine.pacing import compute_pacing_state
from services.learning_engine.eligibility import eligible_learning_nodes
from services.learning_engine.stage_engine import compute_all_subject_states
from services.revision_engine import get_revisions_for_user
from routes_missions import _get_knowledge, _get_recent_mission_node_ids, _get_recent_skipped_node_ids, _get_recent_track_ids
from routes_roadmap import _rollup_from_progress


def digest(rows):
    return sha256(json.dumps(sorted(rows, key=lambda r: r["node_id"]), sort_keys=True, default=str).encode()).hexdigest()


async def verify(db, name):
    matches = await db.users.find({"name": name}, {"_id": 0, "id": 1, "roadmap_version": 1}).to_list(length=2)
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one existing profile: {name}")
    user = matches[0]; uid = user["id"]
    roadmap = get_roadmap(user.get("roadmap_version") or "v1")
    all_rows = await db.knowledge_nodes.find({"user_id": uid}, {"_id": 0}).to_list(length=None)
    before = digest(all_rows)
    onboarding = await db.onboarding.find_one({"user_id": uid}, {"_id": 0}) or {}
    raw = await load_user_progress_rows(db, uid, roadmap.version)
    canonical = build_canonical_progress(roadmap, raw, onboarding)
    plan_rows = planner_progress_rows(roadmap, raw.values(), onboarding)
    plan_map = {row["node_id"]: row for row in plan_rows}
    recorded = [planner_row(row) for row in raw.values()]
    completions = sorted([row for row in recorded if row.get("completion_date")], key=lambda row: row["completion_date"], reverse=True)
    pacing = compute_pacing_state(onboarding.get("interview_target_date"), onboarding.get("daily_study_hours"), count_remaining_learning_nodes(roadmap, plan_map))
    kwargs = dict(onboarding=onboarding, pacing_state=pacing, target_companies=onboarding.get("target_companies"),
                  recent_completions=completions, completed_dates=[row["completion_date"] for row in completions],
                  recent_node_ids=await _get_recent_mission_node_ids(db, uid),
                  skipped_node_ids=await _get_recent_skipped_node_ids(db, uid),
                  recent_track_ids=await _get_recent_track_ids(db, uid), knowledge_rows=await _get_knowledge(db, uid))
    context = build_learner_context(progress_rows=plan_rows, **kwargs)
    eligible = eligible_learning_nodes(plan_map, compute_all_subject_states(roadmap, plan_map), urgency=context.urgency,
                                       virtual_completed_node_ids=context.virtual_completed_node_ids())
    pick = await get_today_learning_node(uid, db=db, company_intelligence=True, learner_intelligence=True, **kwargs)
    after_rows = await db.knowledge_nodes.find({"user_id": uid}, {"_id": 0}).to_list(length=None)
    assert digest(after_rows) == before, "Read-only verification changed state"
    return {
        "name": name, "stored_rows": len(all_rows), "raw_before_sha256": before, "raw_after_sha256": digest(after_rows),
        "unchanged": True, "legacy_rows": sum(bool(legacy_fields(row)) for row in all_rows),
        "certified_rows": sum(bool(certified_fields(row)) for row in all_rows),
        "all_track_identities_resolve": all(row.get("roadmap_version") == roadmap.version and roadmap.get(row["node_id"]) for row in all_rows),
        "tracks": {track: _rollup_from_progress(roadmap.get(track), raw, roadmap, canonical) for track in roadmap.track_ids()},
        "recorded_completion_facts": [{"node_id": row["node_id"], "historical": legacy_fields(row), "certified": certified_fields(row)} for row in all_rows if row.get("completion_date") or certified_fields(row).get("completion_date")],
        "activity_kinds": await db.activity_events.aggregate([{"$match": {"user_id": uid}}, {"$group": {"_id": "$kind", "count": {"$sum": 1}}}]).to_list(length=None),
        "effective_scores": {track: context.effective_knowledge_score(track) for track in roadmap.track_ids()},
        "effective_subjects": sorted(context.effective_completed_subject_ids(roadmap)),
        "eligible_nodes": len(eligible), "recommendation": pick,
        "revision_queue": await get_revisions_for_user(db, uid, roadmap.version, due_only=False),
    }


async def main(args):
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    client = AsyncIOMotorClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=5000)
    try:
        db = client[os.environ["DB_NAME"]]
        results = [await verify(db, name) for name in args.name]
        Path(args.output).write_text(json.dumps({"mode": "read-only; no migration or browser verification",
            "captured_at": datetime.now(timezone.utc).isoformat(), "learners": results}, indent=2, default=str), encoding="utf-8")
        print(json.dumps([{"name": r["name"], "rows": r["stored_rows"], "legacy": r["legacy_rows"], "certified": r["certified_rows"],
                           "preserved": r["unchanged"], "pick": (r["recommendation"] or {}).get("node_id")} for r in results], indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", action="append", required=True)
    parser.add_argument("--output", required=True)
    asyncio.run(main(parser.parse_args()))
