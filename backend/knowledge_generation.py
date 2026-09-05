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
import logging
from datetime import datetime, timezone
from typing import Optional

from ai_service import complete, AICapability, AIProviderError
from prompt_builder import SYSTEM_MESSAGE, build_prompt, parse_content
from roadmap import get_roadmap

logger = logging.getLogger(__name__)


COLLECTION = "knowledge_content"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    """
    if not force:
        cached = await read_cache(db, node_id=node_id, roadmap_version=roadmap_version)
        if cached and cached.get("theory"):
            return cached

    roadmap = get_roadmap(roadmap_version)
    node = roadmap.get(node_id)
    if not node:
        raise AIProviderError("Unknown roadmap node.", kind="not_found", status_code=404)

    prompt = build_prompt(node, roadmap)
    raw = await complete(
        capability=AICapability.KNOWLEDGE_GENERATION,
        system_message=SYSTEM_MESSAGE,
        prompt=prompt,
        session_id=f"kb::{node_id}",
    )
    parsed = parse_content(raw)
    if parsed.get("_parse_error"):
        # We got a response but couldn't parse — do NOT cache garbage.
        logger.warning("KB gen parse error for %s: %s", node_id, parsed.get("_raw", ""))
        raise AIProviderError(
            "AI returned a response that could not be parsed. Please retry.",
            kind="parse_error", status_code=502,
        )

    doc = {
        "node_id": node_id,
        "roadmap_version": roadmap_version,
        "theory": parsed["theory"],
        "examples": parsed["examples"],
        "interview_tips": parsed["interview_tips"],
        "common_mistakes": parsed["common_mistakes"],
        "flashcards": parsed["flashcards"],
        "related_topics": parsed["related_topics"],
        "prerequisites": parsed["prerequisites"],
        "generated_by": user_id,
        "generated_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    await db[COLLECTION].update_one(
        {"node_id": node_id, "roadmap_version": roadmap_version},
        {"$set": doc},
        upsert=True,
    )
    return doc
