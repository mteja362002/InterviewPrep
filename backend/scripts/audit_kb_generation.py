"""KB latency/cache probe. Reads Mongo; captures writes in memory only.

Default mode uses mocked provider content. --live makes ONE real generation
through the unchanged AI Gateway (normal gateway retries may apply).
No production cache is cleared, inserted, or updated.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / '.env')
from motor.motor_asyncio import AsyncIOMotorClient
import knowledge_generation as kg
from roadmap import get_roadmap
from ai_gateway import get_gateway
from ai_gateway.models import AICapability
from ai_gateway.providers.gemini import GeminiAdapter
from ai_gateway.providers.openrouter import OpenRouterAdapter

SAMPLE = json.dumps({'theory': {'beginner': 'Audit content'}, 'examples': [], 'flashcards': []})


class MemoryCache:
    def __init__(self, doc=None):
        self.doc = doc

    async def find_one(self, *args, **kwargs):
        await asyncio.sleep(0)
        return self.doc

    async def update_one(self, query, update, **kwargs):
        self.doc = update['$set']


class MemoryDB:
    def __init__(self, doc=None):
        self.cache = MemoryCache(doc)

    def __getitem__(self, name):
        assert name == kg.COLLECTION
        return self.cache


async def characterize(node_id, version):
    calls = 0
    ready = asyncio.Event()
    async def model(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            ready.set()
        await ready.wait()
        return SAMPLE
    db = MemoryDB()
    kwargs = dict(node_id=node_id, roadmap_version=version, user_id='audit')
    with patch.object(kg, 'complete', side_effect=model):
        await asyncio.wait_for(asyncio.gather(kg.ensure_content(db, **kwargs), kg.ensure_content(db, **kwargs)), timeout=3)
        duplicate_calls = calls
        await kg.ensure_content(db, **kwargs)
        cache_hit_calls = calls - duplicate_calls

    # A synchronous SDK stub establishes whether the actual adapter yields
    # to unrelated coroutines. No network; the production adapter is unchanged.
    unrelated_ran = False
    observed = {}
    async def unrelated():
        nonlocal unrelated_ran
        unrelated_ran = True
    def sync_sdk(**kwargs):
        observed['unrelated_ran_inside_sdk'] = unrelated_ran
        time.sleep(0.1)
        return SimpleNamespace(output_text=SAMPLE)
    fake_client = SimpleNamespace(interactions=SimpleNamespace(create=sync_sdk))
    with patch('google.genai.Client', return_value=fake_client):
        task = asyncio.create_task(unrelated())
        start = time.perf_counter()
        await GeminiAdapter().complete(model='audit', api_key='audit', system_message='', prompt='audit', temperature=0.7, max_tokens=8192, timeout_seconds=30)
        observed['unrelated_ran_when_adapter_returned'] = unrelated_ran
        observed['adapter_ms'] = (time.perf_counter() - start) * 1000
        await task
    return {'concurrent_cache_miss_provider_calls': duplicate_calls, 'subsequent_cache_hit_provider_calls': cache_hit_calls, 'sync_adapter_probe': observed}


async def main(args):
    roadmap = get_roadmap()
    node = roadmap.get(args.node)
    if not node:
        raise ValueError('Unknown roadmap node')
    result = {'node': args.node, 'roadmap_version': roadmap.version, 'production_writes': 0,
              'characterization': await characterize(args.node, roadmap.version)}
    client = AsyncIOMotorClient(os.environ['MONGO_URL'], serverSelectionTimeoutMS=5000)
    try:
        db = client[os.environ['DB_NAME']]
        start = time.perf_counter()
        cached = await kg.read_cache(db, node_id=args.node, roadmap_version=roadmap.version)
        result['mongo_first_cache_lookup_ms'] = (time.perf_counter() - start) * 1000
        start = time.perf_counter()
        await kg.read_cache(db, node_id=args.node, roadmap_version=roadmap.version)
        result['mongo_warm_cache_lookup_ms'] = (time.perf_counter() - start) * 1000
        result['mongo_cache_hit'] = bool(cached and cached.get('theory'))
        result['mongo_cache_indexes'] = await db[kg.COLLECTION].index_information()
        result['mongo_cached_documents'] = await db[kg.COLLECTION].count_documents({})
    finally:
        client.close()

    gateway = get_gateway()
    gateway.initialise()
    profile = gateway._capability_registry.resolve(AICapability.KNOWLEDGE_GENERATION)
    chain = gateway._routing_policy.resolve_chain(AICapability.KNOWLEDGE_GENERATION, gateway._provider_registry)
    result['configured_chain'] = [{'provider': p.id, 'models': gateway._model_selector.select_candidates(capability=AICapability.KNOWLEDGE_GENERATION, profile=profile, provider=p)} for p in chain]

    if args.live:
        measurements = {'adapter_attempts': []}
        original_complete = kg.complete
        original_prompt = kg.build_prompt
        original_parse = kg.parse_content
        def prompt(*a, **kw):
            start = time.perf_counter()
            value = original_prompt(*a, **kw)
            measurements['prompt_build_ms'] = (time.perf_counter() - start) * 1000
            measurements['prompt_chars'] = len(value)
            return value
        def parse(*a, **kw):
            start = time.perf_counter()
            value = original_parse(*a, **kw)
            measurements['parse_validate_ms'] = (time.perf_counter() - start) * 1000
            measurements['response_chars'] = len(a[0])
            return value
        async def complete(**kw):
            start = time.perf_counter()
            try:
                return await original_complete(**kw)
            finally:
                measurements['facade_gateway_ms'] = (time.perf_counter() - start) * 1000
        def adapter_wrapper(original, provider):
            async def wrapped(self, **kw):
                start = time.perf_counter()
                attempt = {'provider': provider, 'model': kw['model']}
                try:
                    return await original(self, **kw)
                except Exception as exc:
                    attempt['error_type'] = type(exc).__name__
                    raise
                finally:
                    attempt['ms'] = (time.perf_counter() - start) * 1000
                    measurements['adapter_attempts'].append(attempt)
            return wrapped
        event_loop_lags = []
        async def ticker():
            while True:
                start = time.perf_counter()
                await asyncio.sleep(0.02)
                event_loop_lags.append(max(0, (time.perf_counter() - start) * 1000 - 20))
        ticker_task = asyncio.create_task(ticker())
        await asyncio.sleep(0)
        start = time.perf_counter()
        try:
            with patch.object(kg, 'complete', side_effect=complete), patch.object(kg, 'build_prompt', side_effect=prompt), patch.object(kg, 'parse_content', side_effect=parse), patch.object(GeminiAdapter, 'complete', adapter_wrapper(GeminiAdapter.complete, 'gemini')), patch.object(OpenRouterAdapter, 'complete', adapter_wrapper(OpenRouterAdapter.complete, 'openrouter')):
                await kg.ensure_content(MemoryDB(), node_id=args.node, roadmap_version=roadmap.version, user_id='audit')
            measurements['success'] = True
        except Exception as exc:
            measurements['success'] = False
            measurements['error_type'] = type(exc).__name__
            measurements['error_kind'] = getattr(exc, 'kind', None)
        finally:
            measurements['generation_total_ms'] = (time.perf_counter() - start) * 1000
            await asyncio.sleep(0)
            ticker_task.cancel()
            await asyncio.gather(ticker_task, return_exceptions=True)
        measurements['max_event_loop_lag_ms'] = max(event_loop_lags, default=0)
        measurements['mongo_write_ms'] = None
        measurements['note'] = 'Real provider request; cache miss/write simulated in memory. Not a browser or HTTP latency measurement.'
        result['live_probe'] = measurements
    Path(args.output).write_text(json.dumps(result, indent=2, default=str), encoding='utf-8')
    print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--live', action='store_true')
    asyncio.run(main(parser.parse_args()))
