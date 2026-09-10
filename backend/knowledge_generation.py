"""Knowledge-content orchestration.

Responsibilities:
  1. Read cache from Mongo (`knowledge_content` collection).
  2. On miss, call the AI Gateway via `ai_service.complete()`.
  3. Parse + persist the response.
  4. Return the cached dict to the caller.

Cache scope is GLOBAL (node_id, roadmap_version) — the first user pays the
generation cost; everybody else reads cache. This matches the "minimize API
usage and cost" requirement in the product brief.
"""
from __future__ import annotations
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from ai_service import complete, AICapability, AIProviderError
from prompt_builder import SYSTEM_MESSAGE, build_prompt, parse_content
from roadmap import get_roadmap

logger = logging.getLogger(__name__)


COLLECTION = "knowledge_content"

# Single-flight locks: prevent duplicate concurrent AI calls for the same node.
# Key: (node_id, roadmap_version) → asyncio.Lock
#
# SCOPE LIMITATION — this is a PROCESS-LOCAL lock.
# It de-duplicates concurrent requests within one event loop only. If the
# backend is ever run with multiple worker processes (uvicorn --workers N,
# gunicorn, or >1 container replica), each process keeps its own
# `_generation_locks` dict and N concurrent first-requests for the same node
# would produce up to N provider calls.
#
# This is adequate for the current deployment: the repo declares uvicorn as a
# plain dependency with no Dockerfile, no gunicorn, no `--workers` flag and no
# WEB_CONCURRENCY setting anywhere, i.e. the default single-process server.
# Correctness does not depend on the lock in any case — the cache is keyed on
# (node_id, roadmap_version) and the write is an idempotent upsert, so the
# worst multi-process outcome is redundant cost, never corruption.
#
# Deliberately NOT introducing distributed locking (Redis/Mongo advisory
# locks): that infrastructure is unwarranted until the deployment actually
# runs multiple workers. Revisit this comment if that changes.
_generation_locks: dict[tuple[str, str], asyncio.Lock] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _deterministic_related(node: dict, roadmap) -> dict:
    """Pre-populate related_topics and prerequisites from the roadmap graph.

    These sections are fully deterministic — they come from authored
    prerequisite/related edges and sibling relationships in the DAG.
    Available immediately without an AI call.
    """
    related = []
    for rid in (node.get("related") or [])[:8]:
        r = roadmap.get(rid) if hasattr(roadmap, "get") else None
        if r:
            related.append({"id": rid, "label": r.get("label", rid), "why": "Related topic in the roadmap.",
                            "source": "roadmap"})

    prerequisites = []
    for pid in (node.get("prerequisites") or [])[:8]:
        p = roadmap.get(pid) if hasattr(roadmap, "get") else None
        if p:
            prerequisites.append({"id": pid, "label": p.get("label", pid), "why": "Prerequisite in the roadmap.",
                                  "source": "roadmap"})

    # Siblings (same category/module)
    cat = node.get("category")
    if cat and hasattr(roadmap, "get"):
        parent = roadmap.get(cat)
        if parent:
            for cid in (parent.get("child_ids") or [])[:6]:
                if cid == node.get("id"):
                    continue
                sib = roadmap.get(cid)
                if sib:
                    related.append({"id": cid, "label": sib.get("label", cid), "why": "Sibling topic.",
                                    "source": "roadmap"})

    return {"related_topics": related[:8], "prerequisites": prerequisites[:4]}


def _merge_relationships(deterministic: dict, parsed: dict) -> dict:
    """Merge canonical roadmap edges with AI suggestions.

    Canonical roadmap relationships are AUTHORITATIVE; AI output is
    supplementary enrichment only.  An AI suggestion may ADD an edge the
    roadmap does not declare, but must never replace, redefine or rank ahead
    of an authored prerequisite/related edge — so canonical entries come
    first and win every id collision.  Entries carry a ``source`` marker
    ("roadmap" | "ai") so consumers can tell the two tiers apart.

    Pure function — deterministic for a given (deterministic, parsed) pair.
    """
    ai_related = parsed.get("related_topics") or []
    ai_prereqs = parsed.get("prerequisites") or []
    canonical_related = deterministic.get("related_topics") or []
    canonical_prereqs = deterministic.get("prerequisites") or []
    canonical_related_ids = {r.get("id") for r in canonical_related if r.get("id")}
    canonical_prereq_ids = {p.get("id") for p in canonical_prereqs if p.get("id")}
    return {
        "related_topics": canonical_related + [
            {**r, "source": "ai"} for r in ai_related
            if r.get("id") not in canonical_related_ids
        ],
        "prerequisites": canonical_prereqs + [
            {**p, "source": "ai"} for p in ai_prereqs
            if p.get("id") not in canonical_prereq_ids
        ],
    }


async def read_cache(db, *, node_id: str, roadmap_version: str) -> Optional[dict]:
    """Return the cached content dict for a node, or None."""
    doc = await db[COLLECTION].find_one(
        {"node_id": node_id, "roadmap_version": roadmap_version},
        {"_id": 0},
    )
    return doc


async def clear_cache(db, *, node_id: str, roadmap_version: str) -> int:
    """Force a re-generation next time. Returns rows removed."""
    res = await db[COLLECTION].delete_many(
        {"node_id": node_id, "roadmap_version": roadmap_version},
    )
    return res.deleted_count


async def ensure_content(
    db,
    *,
    node_id: str,
    roadmap_version: str,
    user_id: str,
    force: bool = False,
) -> dict:
    """Return content for a node, generating it via AI on first request.

    Raises AIProviderError with a user-facing `.kind` on failure so the
    calling route can shape the HTTP response.

    Timing instrumentation: the returned dict includes `_timing` with
    per-phase latency in milliseconds.
    """
    t0 = time.monotonic()
    timing: dict[str, float] = {}

    # ---- Cache check ------------------------------------------------
    if not force:
        cached = await read_cache(db, node_id=node_id, roadmap_version=roadmap_version)
        timing["cache_check_ms"] = round((time.monotonic() - t0) * 1000, 1)
        if cached and cached.get("theory"):
            timing["cache_hit"] = True
            timing["total_ms"] = round((time.monotonic() - t0) * 1000, 1)
            cached["_timing"] = timing
            return cached

    # ---- Single-flight lock -----------------------------------------
    lock_key = (node_id, roadmap_version)
    if lock_key not in _generation_locks:
        _generation_locks[lock_key] = asyncio.Lock()
    lock = _generation_locks[lock_key]

    async with lock:
        # Double-check cache after acquiring lock (another request
        # may have generated content while we waited).
        if not force:
            cached = await read_cache(db, node_id=node_id, roadmap_version=roadmap_version)
            if cached and cached.get("theory"):
                timing["cache_hit"] = True
                timing["waited_for_lock"] = True
                timing["total_ms"] = round((time.monotonic() - t0) * 1000, 1)
                cached["_timing"] = timing
                return cached

        # ---- Roadmap lookup -----------------------------------------
        roadmap = get_roadmap(roadmap_version)
        node = roadmap.get(node_id)
        if not node:
            raise AIProviderError("Unknown roadmap node.", kind="not_found", status_code=404)

        # ---- Pre-populate deterministic sections --------------------
        deterministic = _deterministic_related(node, roadmap)

        # ---- AI generation ------------------------------------------
        t_gen = time.monotonic()
        prompt = build_prompt(node, roadmap)
        raw = await complete(
            capability=AICapability.KNOWLEDGE_GENERATION,
            system_message=SYSTEM_MESSAGE,
            prompt=prompt,
            session_id=f"kb::{node_id}",
        )
        timing["generation_ms"] = round((time.monotonic() - t_gen) * 1000, 1)

        # ---- Parse --------------------------------------------------
        t_parse = time.monotonic()
        parsed = parse_content(raw)
        timing["parse_ms"] = round((time.monotonic() - t_parse) * 1000, 1)

        if parsed.get("_parse_error"):
            logger.warning("KB gen parse error for %s: %s", node_id, parsed.get("_raw", ""))
            raise AIProviderError(
                "AI returned a response that could not be parsed. Please retry.",
                kind="parse_error", status_code=502,
            )

        merged = _merge_relationships(deterministic, parsed)
        merged_related = merged["related_topics"]
        merged_prereqs = merged["prerequisites"]

        # ---- Persist ------------------------------------------------
        t_persist = time.monotonic()
        doc = {
            "node_id": node_id,
            "roadmap_version": roadmap_version,
            "theory": parsed["theory"],
            "examples": parsed["examples"],
            "interview_tips": parsed["interview_tips"],
            "common_mistakes": parsed["common_mistakes"],
            "flashcards": parsed["flashcards"],
            "related_topics": merged_related,
            "prerequisites": merged_prereqs,
            "generated_by": user_id,
            "generated_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        await db[COLLECTION].update_one(
            {"node_id": node_id, "roadmap_version": roadmap_version},
            {"$set": doc},
            upsert=True,
        )
        timing["persist_ms"] = round((time.monotonic() - t_persist) * 1000, 1)
        timing["cache_hit"] = False
        timing["total_ms"] = round((time.monotonic() - t0) * 1000, 1)
        doc["_timing"] = timing

        logger.info(
            "KB content generated for %s: gen=%.0fms parse=%.0fms persist=%.0fms total=%.0fms",
            node_id,
            timing.get("generation_ms", 0),
            timing.get("parse_ms", 0),
            timing.get("persist_ms", 0),
            timing["total_ms"],
        )
        return doc
