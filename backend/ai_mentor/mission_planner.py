"""Adaptive Mission Planner — the AI half of the Mission Engine.

This module DOES NOT replace the existing deterministic mission generator
(`routes_missions._generate_today_mission` + `mission_engine.build_mission_for_user`).
It ADDS an optional AI layer on top:

  * A short "why this mission today" narrative that references the learner's
    weak areas, prereq chain, and target companies.
  * A "Tomorrow Preview" — an outline (not a persisted mission) hinting at
    what the mentor would generate next.
  * A "This Week Goal" — a 5-7 day trajectory.

The planner is:
  * IDEMPOTENT — narrative + previews are cached on the mission doc itself
    (`tomorrow_preview`, `week_goal`, `ai_narrative`). Regenerated only when
    absent. Refreshing the page never re-invokes the LLM.
  * PREREQUISITE-AWARE — reuses `context_builder` which walks
    `roadmap.prerequisites` transitively; the LLM is given the RECOMMENDED
    NEXT STEP and told to obey it.
  * GRACEFULLY DEGRADED — if the AI call fails, the mission still returns
    without preview fields.

Uses `ai_service.complete()` routed through the AI Gateway with automatic
provider failover.
"""
from __future__ import annotations
import json
import logging
import re
from typing import Any, Dict, Optional

from ai_service import complete, AICapability, AIProviderError

from .context_builder import build_context, serialize_context

logger = logging.getLogger(__name__)

_JSON_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


_PLANNER_SYSTEM = """You are the **PrepOS Adaptive Mission Planner**.
Your job is to look at the learner's context and emit a short JSON envelope
with two forecasts + a one-line narrative. You do NOT design today's mission
(that has already been chosen by the deterministic engine); you EXPLAIN why
it's the right mission and preview what's next.

Hard rules:
  * PREREQUISITE-AWARE: NEVER recommend an advanced topic ahead of an
    incomplete prerequisite. If the context surfaces a "RECOMMENDED NEXT
    STEP", your `tomorrow_preview.focus` must respect it.
  * LOW-CONFIDENCE ROUTING: if the learner's weak topics have confidence < 5,
    tomorrow_preview should emphasise revision + easy problems + concept
    strengthening — NOT new advanced material.
  * TARGET-COMPANY AWARENESS: mention the learner's target companies when
    justifying the week's trajectory.
  * TERSE. This lives inside the mission card, not a blog post.

Emit VALID JSON ONLY (no prose, no fences) matching this schema exactly:
{
  "narrative": "1-2 sentence explanation of why today's mission is the right next step for this learner (reference weak areas / prereqs / target companies by name).",
  "tomorrow_preview": {
    "focus": "Short topic label (obey prereq chain)",
    "why": "1 sentence — why this comes next based on today's mission + prereqs",
    "estimated_duration": 60
  },
  "week_goal": {
    "headline": "5-8 words — the outcome by end of week",
    "milestones": ["day 1-2: ...", "day 3-4: ...", "day 5-7: ..."],
    "target_companies": ["Google", "..."]
  }
}"""


def _parse_json(raw: str) -> Optional[dict]:
    """Same tolerant parser used by the mentor lesson mode."""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        pass
    m = _JSON_FENCE.search(raw)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    if "{" in raw and "}" in raw:
        try:
            return json.loads(raw[raw.find("{") : raw.rfind("}") + 1])
        except Exception:
            pass
    return None


def _mission_snapshot(mission: dict) -> str:
    """Compact snapshot of today's mission the planner needs to reason about."""
    tasks = mission.get("tasks") or []
    task_lines = [
        f"- [{t.get('kind') or t.get('type') or 'task'}] {t.get('title') or t.get('topic')}"
        f" ({t.get('estimated_minutes') or t.get('duration') or '?'}m)"
        for t in tasks[:8]
    ]
    return (
        f"**Today's mission**: {mission.get('title')}\n"
        f"Focus area: {mission.get('focus_area')} · topic: {mission.get('focus_topic')}\n"
        f"Difficulty: {mission.get('difficulty')} · duration: {mission.get('estimated_duration_minutes')}m\n"
        f"Learning objective: {mission.get('learning_objective')}\n"
        f"Tasks:\n" + "\n".join(task_lines)
    )


async def generate_narrative_and_previews(db, *, user_id: str, mission: dict) -> Dict[str, Any]:
    """One AI call → narrative + tomorrow_preview + week_goal.

    Silent no-op if the AI call fails — mission still displays without
    the AI layer. This is critical: mission generation must NEVER fail
    because of an AI outage.
    """
    context = await build_context(db, user_id=user_id, node_id=None)
    context_block = serialize_context(context)
    system_message = f"{_PLANNER_SYSTEM}\n\n---\n**LEARNER CONTEXT**:\n{context_block}"
    prompt = f"{_mission_snapshot(mission)}\n\nEmit the JSON envelope now."

    try:
        raw = await complete(
            capability=AICapability.MISSION_NARRATIVE,
            system_message=system_message,
            prompt=prompt,
            session_id=f"mission-planner::{user_id}",
        )
    except AIProviderError as e:
        logger.warning("mission_planner: AI call failed (%s) — falling back to no-narrative mission", e.kind)
        return {}
    except Exception as e:  # noqa: BLE001
        logger.exception("mission_planner: unexpected failure — %s", e)
        return {}

    parsed = _parse_json(raw)
    if not parsed:
        logger.warning("mission_planner: could not parse JSON envelope")
        return {}

    return {
        "ai_narrative": (parsed.get("narrative") or "").strip() or None,
        "tomorrow_preview": parsed.get("tomorrow_preview") or None,
        "week_goal": parsed.get("week_goal") or None,
    }


async def enrich_mission(db, *, user_id: str, mission_doc: dict) -> dict:
    """Attach AI narrative + previews to a mission doc if not already present.

    Called once per calendar day (guaranteed by the idempotency check in
    `_generate_today_mission`). Writes back to Mongo so subsequent GETs are
    served from cache without another LLM call.
    """
    # Fast-path: already enriched.
    if mission_doc.get("ai_narrative") or mission_doc.get("tomorrow_preview") or mission_doc.get("week_goal"):
        return mission_doc

    extras = await generate_narrative_and_previews(db, user_id=user_id, mission=mission_doc)
    if not extras:
        return mission_doc

    await db.daily_missions.update_one(
        {"id": mission_doc["id"]},
        {"$set": {k: v for k, v in extras.items() if v is not None}},
    )
    mission_doc.update({k: v for k, v in extras.items() if v is not None})
    return mission_doc
