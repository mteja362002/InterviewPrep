"""Read-only learner-path audit. Never calls mission/onboarding write routes.

Run from backend: .venv/Scripts/python scripts/audit_learner_paths.py
  --name 'Display Name' [--name ...] --output ../test_reports/learner_paths.json
Names are lookup parameters only; every learner follows the same trace.
"""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from time import perf_counter
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / '.env')

from motor.motor_asyncio import AsyncIOMotorClient
from roadmap import get_roadmap
from models import OnboardingSelfAssessment
from services.progress_engine import (
    build_canonical_progress, count_remaining_learning_nodes,
    load_user_progress_rows, seed_knowledge_nodes_from_self_assessment,
)
from services.learning_engine.context import build_learner_context
from services.learning_engine.eligibility import eligible_learning_nodes
from services.learning_engine.pacing import compute_pacing_state
from services.learning_engine.priority_engine import score_candidate
from services.learning_engine.stage_engine import compute_all_subject_states
from services.learning_engine.subject_progression import build_all_sessions, build_daily_learning_plan
from services.learning_engine import planner
from routes_roadmap import _rollup_from_progress
from routes_missions import (
    _get_knowledge, _get_recent_mission_node_ids, _get_recent_skipped_node_ids,
    _get_recent_track_ids, _get_due_revisions, _get_recent_feedback,
    _count_extra_practice_yesterday,
)
from mission_engine import build_mission_for_user


class MemoryCursor:
    def __init__(self, rows):
        self.rows = rows

    async def to_list(self, length=None):
        return self.rows[:length] if length else list(self.rows)


class MemoryCollection:
    def __init__(self):
        self.rows = []

    def find(self, query, projection=None):
        return MemoryCursor([r for r in self.rows if all(r.get(k) == v for k, v in query.items())])

    async def insert_many(self, rows):
        self.rows.extend(rows)


class MemoryDB:
    def __init__(self):
        self.knowledge_nodes = MemoryCollection()


async def pf_matrix():
    roadmap = get_roadmap()
    results = []
    for rating in (0, 7, 9, 10):
        db = MemoryDB()
        scores = OnboardingSelfAssessment(programming_fundamentals=rating).model_dump()
        onboarding = {'self_assessment': scores, 'current_position': 'student'}
        await seed_knowledge_nodes_from_self_assessment(db, 'audit', scores, roadmap)
        rows = db.knowledge_nodes.rows
        before = json.dumps(rows, sort_keys=True)
        context = build_learner_context(onboarding=onboarding, progress_rows=rows)
        canonical = build_canonical_progress(roadmap, context.progress_map)
        recommendation = await planner.get_today_learning_node('audit', db=db, onboarding=onboarding)
        assert before == json.dumps(rows, sort_keys=True), 'Planner must not persist virtual evidence'
        pf_rows = [r for r in rows if roadmap.get(r['node_id'])['track'] == 'programming_fundamentals']
        results.append({
            'rating': rating, 'seed_rows': len(pf_rows),
            'effective_score': context.effective_knowledge_score('programming_fundamentals'),
            'effective_completed': 'programming_fundamentals' in context.effective_completed_subject_ids(roadmap),
            'canonical': canonical['programming_fundamentals'],
            'kb': _rollup_from_progress(roadmap.get('programming_fundamentals'), context.progress_map, roadmap, canonical),
            'mission_node': recommendation['node_id'] if recommendation else None,
            'virtual_evidence_persisted': False,
        })
    return results


async def trace_learner(db, name):
    users = await db.users.find({'name': name}, {'_id': 0, 'id': 1}).to_list(length=2)
    if len(users) != 1:
        return {'name': name, 'error': f'Expected one exact name match, found {len(users)}'}
    uid = users[0]['id']
    onboarding = await db.onboarding.find_one({'user_id': uid}, {'_id': 0}) or {}
    roadmap = get_roadmap()
    progress = await load_user_progress_rows(db, uid)
    rows = list(progress.values())
    canonical = build_canonical_progress(roadmap, progress)
    knowledge = await _get_knowledge(db, uid)
    recent_nodes = await _get_recent_mission_node_ids(db, uid)
    skipped = await _get_recent_skipped_node_ids(db, uid)
    recent_tracks = await _get_recent_track_ids(db, uid)
    completions = sorted([r for r in rows if r.get('completion_date')], key=lambda r: r['completion_date'], reverse=True)
    pacing = compute_pacing_state(onboarding.get('interview_target_date'), onboarding.get('daily_study_hours'), count_remaining_learning_nodes(roadmap, progress))
    kwargs = dict(onboarding=onboarding, pacing_state=pacing, target_companies=onboarding.get('target_companies'),
                  completed_dates=[r['completion_date'] for r in completions], recent_completions=completions,
                  recent_node_ids=recent_nodes, recent_track_ids=recent_tracks, skipped_node_ids=skipped,
                  knowledge_rows=knowledge)
    ctx = build_learner_context(progress_rows=rows, company_intelligence_enabled=True, learner_intelligence_enabled=True, **kwargs)
    states = compute_all_subject_states(roadmap, progress)
    virtual = ctx.virtual_completed_node_ids()
    eligible = eligible_learning_nodes(progress, states, urgency=ctx.urgency, virtual_completed_node_ids=virtual)
    eligible_ids = {n['id'] for n in eligible}
    effective_subjects = ctx.effective_completed_subject_ids(roadmap)
    sessions = build_all_sessions(roadmap, progress, effective_completed_subjects=effective_subjects)
    plan = build_daily_learning_plan(sessions, roadmap, recent_track_ids=recent_tracks)
    scored_ids = []
    def record_score(node, context):
        scored_ids.append(node['id'])
        return score_candidate(node, context)
    with patch.object(planner, 'score_candidate', side_effect=record_score):
        recommendation = await planner.get_today_learning_node(uid, db=db, company_intelligence=True, learner_intelligence=True, **kwargs)
    mission, adjustment = build_mission_for_user(
        uid, onboarding, knowledge, await _get_due_revisions(db, uid),
        recent_feedback=await _get_recent_feedback(db, uid, hours=36),
        extra_practice_count_yesterday=await _count_extra_practice_yesterday(db, uid),
        knowledge_nodes=progress, learning_recommendation=recommendation, pacing_state=pacing,
    )
    cached = await db.daily_missions.find({'user_id': uid}, {'_id': 0, 'date': 1, 'focus_topic': 1, 'focus_subtopic': 1, 'title': 1, 'recommendation_insight': 1, 'tasks.node_id': 1}).sort('date', -1).limit(4).to_list(length=4)
    by_track = {}
    for track in roadmap.track_ids():
        track_rows = [r for r in rows if (roadmap.get(r['node_id']) or {}).get('track') == track]
        by_track[track] = {
            'declared': ctx.onboarding_scores.get(track), 'effective': ctx.effective_knowledge_score(track),
            'rows': len(track_rows), 'rows_with_track': sum(bool(r.get('track')) for r in track_rows),
            'statuses': dict(Counter(r.get('status') for r in track_rows)),
            'completion_dates': sum(bool(r.get('completion_date')) for r in track_rows),
            'attempts': sum(r.get('attempts', 0) for r in track_rows),
            'context_evidence_count': ctx.track_completion_count(track),
            'canonical': canonical[track], 'session': asdict(sessions[track]),
            'learning_state': states[track].to_dict(),
            'kb': _rollup_from_progress(roadmap.get(track), progress, roadmap, canonical),
        }
    candidates = []
    ids = eligible_ids | {s.next_node_id for s in sessions.values() if s.next_node_id}
    for node_id in sorted(ids):
        node = roadmap.get(node_id)
        prereqs = (roadmap.get(node['track']) or {}).get('subject_prerequisites', [])
        candidates.append({
            'node_id': node_id, 'track': node['track'], 'stage': node.get('learning_stage'),
            'subject_prerequisites': {p: p in effective_subjects for p in prereqs},
            'node_prerequisites': node.get('prerequisites', []),
            'eligibility_engine': node_id in eligible_ids,
            'session_plan': node_id in {p.node_id for p in plan.task_plans},
            'actually_scored_in_primary_session_loop': node_id in scored_ids,
            'breakdown': score_candidate(node, ctx).breakdown,
        })
    return {
        'name': name,
        'onboarding': {k: onboarding.get(k) for k in ('self_assessment', 'current_position', 'target_companies', 'interview_target_date', 'daily_study_hours')},
        'pacing': pacing, 'recent_tracks': recent_tracks, 'recent_nodes': recent_nodes,
        'skipped_nodes': skipped, 'tracks': by_track,
        'effective_subjects': sorted(effective_subjects), 'virtual_node_count': len(virtual),
        'eligible_counts': dict(Counter(n['track'] for n in eligible)),
        'session_plan_nodes': [p.node_id for p in plan.task_plans],
        'primary_loop_scored_nodes': scored_ids,
        'candidates': candidates, 'recommendation': recommendation,
        'recomposed_mission': {'title': mission.title, 'focus_topic': mission.focus_topic, 'task_nodes': [t.node_id for t in mission.tasks], 'validation': adjustment.get('validation')},
        'cached_missions': cached,
        'java_modules': [{'id': m['id'], 'canonical': canonical[m['id']], 'children': [{'id': c['id'], 'canonical': canonical[c['id']]} for c in roadmap.children(m['id'])]} for m in roadmap.children('java')],
    }


async def main(args):
    client = AsyncIOMotorClient(os.environ['MONGO_URL'], serverSelectionTimeoutMS=5000)
    try:
        db = client[os.environ['DB_NAME']]
        started = perf_counter()
        result = {'captured_at': datetime.now(timezone.utc).isoformat(), 'mode': 'read-only database; pure mission recomposition, no route generation', 'pf_matrix': await pf_matrix()}
        result['learners'] = [await trace_learner(db, name) for name in args.name]
        result['audit_seconds'] = perf_counter() - started
        Path(args.output).write_text(json.dumps(result, indent=2, default=str), encoding='utf-8')
        print(json.dumps({'output': args.output, 'seconds': result['audit_seconds'], 'learners': [{'name': r['name'], 'selected': (r.get('recommendation') or {}).get('node_id'), 'eligible': r.get('eligible_counts'), 'session_plan': r.get('session_plan_nodes')} for r in result['learners']]}, indent=2))
    finally:
        client.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', action='append', default=[])
    parser.add_argument('--output', required=True)
    asyncio.run(main(parser.parse_args()))
