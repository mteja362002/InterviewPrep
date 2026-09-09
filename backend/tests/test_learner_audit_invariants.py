"""Preserved contracts from the September learner-state forensic audit.

These tests do not choose a new KB baseline/display semantic. They protect
the already approved distinction between planner virtual state and writes.
"""
import asyncio
from copy import deepcopy

import pytest

import knowledge_generation
from roadmap import get_roadmap
from services.learning_engine.context import build_learner_context
from services.learning_engine.planner import get_today_learning_node
from services.progress_engine import seed_knowledge_nodes_from_self_assessment
from tests.test_onboarding_knowledge_seed import FakeDB


@pytest.mark.parametrize('rating', [0, 7, 9, 10])
def test_declared_pf_can_unlock_planning_without_persisting_learning_evidence(rating):
    async def scenario():
        roadmap = get_roadmap()
        scores = {track: 0 for track in roadmap.track_ids()}
        scores['programming_fundamentals'] = rating
        db = FakeDB()
        await seed_knowledge_nodes_from_self_assessment(db, 'learner-audit', scores, roadmap)
        before = deepcopy(db.knowledge_nodes._rows)
        onboarding = {'self_assessment': scores, 'current_position': 'student'}
        context = build_learner_context(onboarding=onboarding, progress_rows=before)
        assert context.effective_knowledge_score('programming_fundamentals') == rating * 10
        assert ('programming_fundamentals' in context.effective_completed_subject_ids(roadmap)) == (rating >= 7)
        pick = await get_today_learning_node('learner-audit', db=db, onboarding=onboarding)
        assert pick is not None
        if rating >= 7:
            assert pick['track'] != 'programming_fundamentals'
        assert db.knowledge_nodes._rows == before
        assert not any(row.get('completion_date') or row.get('attempts') for row in before)
    asyncio.run(scenario())


def test_global_content_cache_hit_does_not_invoke_gateway_or_write(monkeypatch):
    cached = {'node_id': 'cached-topic', 'roadmap_version': 'v1',
              'theory': {'beginner': 'Existing shared content'}, 'generated_by': 'another-learner'}

    class Collection:
        async def find_one(self, query, projection):
            assert query == {'node_id': 'cached-topic', 'roadmap_version': 'v1'}
            return cached

    class DB:
        def __getitem__(self, name):
            assert name == 'knowledge_content'
            return Collection()

    async def forbidden_generation(**kwargs):
        pytest.fail('A cache hit must not generate content')

    monkeypatch.setattr(knowledge_generation, 'complete', forbidden_generation)
    result = asyncio.run(knowledge_generation.ensure_content(
        DB(), node_id='cached-topic', roadmap_version='v1', user_id='new-learner',
    ))
    assert result == cached
