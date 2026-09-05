"""Prompt builder for AI knowledge-base generation.

Produces a strict JSON-mode prompt for the given roadmap node. The output
of Gemini is parsed by `parse_content()` — malformed responses fall back
to sensible empty defaults rather than crashing the caller.
"""
from __future__ import annotations
from typing import Any

from ai_gateway.parsers import parse_llm_json


SYSTEM_MESSAGE = (
    "You are PrepOS Mentor — an interview coach for software engineers targeting "
    "product-based companies (Google, Microsoft, Uber, Atlassian, Adobe, LinkedIn, "
    "Stripe, PhonePe, Flipkart, Goldman Sachs, PayPal, Salesforce, Oracle, Zoho). "
    "You produce concise, high-signal interview content. Never invent APIs, "
    "libraries or study links. Prefer canonical explanations over trivia. "
    "Return STRICT JSON — no markdown code fences, no prose outside JSON."
)


def _related_context(node: dict, roadmap) -> str:
    """Build a compact list of nearby roadmap node ids so the model can wire
    Related Topics / Prerequisites back into real roadmap entries."""
    lines: list[str] = []
    for pid in (node.get("prerequisites") or [])[:8]:
        p = roadmap.get(pid) if hasattr(roadmap, "get") else None
        if p:
            lines.append(f"- prereq: {pid} ({p.get('label')})")
    for rid in (node.get("related") or [])[:8]:
        r = roadmap.get(rid) if hasattr(roadmap, "get") else None
        if r:
            lines.append(f"- related: {rid} ({r.get('label')})")
    # Siblings (same category/module) — cheap suggestion source.
    cat = node.get("category")
    if cat and hasattr(roadmap, "get"):
        parent = roadmap.get(cat)
        if parent:
            for cid in (parent.get("child_ids") or [])[:8]:
                if cid == node["id"]:
                    continue
                sib = roadmap.get(cid)
                if sib:
                    lines.append(f"- sibling: {cid} ({sib.get('label')})")
    return "\n".join(lines[:24]) or "- (no explicit graph neighbors)"


def build_prompt(node: dict, roadmap) -> str:
    """Build the user prompt Gemini should answer for one node."""
    label = node.get("label") or node.get("id")
    track = node.get("track") or "cs"
    module = node.get("module") or ""
    category = node.get("category") or ""
    difficulty = node.get("difficulty") or "medium"
    tags = ", ".join(node.get("tags") or [])
    description = node.get("description") or ""
    interview_freq = node.get("interview_frequency") or 3
    context = _related_context(node, roadmap)

    return f"""Generate interview-prep knowledge for the following topic.

TOPIC: {label}
TRACK: {track}
MODULE: {module}
CATEGORY: {category}
DIFFICULTY: {difficulty}
TAGS: {tags}
INTERVIEW_FREQUENCY (1-5): {interview_freq}
DESCRIPTION: {description}

NEIGHBORING_ROADMAP_NODES (use these IDs verbatim when citing prerequisites / related):
{context}

Produce a single JSON object with EXACTLY these keys (no extras, no nulls):

{{
  "theory": {{
    "beginner": "One paragraph, plain English, 2-4 sentences.",
    "deep": "3-6 paragraphs. Cover the intuition and the mechanics.",
    "real_world": "One paragraph tying the concept to something a working engineer builds.",
    "architecture": "One paragraph on how this fits into a larger system.",
    "advantages": ["3-5 short bullet strings."],
    "disadvantages": ["3-5 short bullet strings."],
    "when_to_use": ["2-4 short bullet strings."],
    "when_not_to_use": ["2-4 short bullet strings."],
    "interview_summary": "The 30-second answer a candidate should give in a live round."
  }},
  "examples": [
    {{ "title": "Short example name",
       "scenario": "One paragraph describing a realistic software-engineering scenario.",
       "walkthrough": "2-4 sentences on how the concept solves it." }}
  ],
  "interview_tips": [
    "3-6 short strings. Real product-based-company advice — signal, not fluff."
  ],
  "common_mistakes": [
    {{ "mistake": "What people get wrong.", "fix": "How to avoid it." }}
  ],
  "flashcards": [
    {{ "q": "Question", "a": "Concise answer under 30 words." }}
  ],
  "related_topics": [
    {{ "id": "roadmap-node-id-from-context-above-or-empty-string",
       "label": "Human label", "why": "One sentence." }}
  ],
  "prerequisites": [
    {{ "id": "roadmap-node-id-from-context-above-or-empty-string",
       "label": "Human label", "why": "One sentence." }}
  ]
}}

RULES:
- Return ONLY valid JSON. No markdown, no code fences, no commentary before or after.
- 6-10 flashcards. 3-5 examples. 4-6 common mistakes. 3-6 related. 2-4 prerequisites.
- Use the exact roadmap node IDs from NEIGHBORING_ROADMAP_NODES when possible; use "" if none fit.
"""


def parse_content(raw: str) -> dict:
    """Parse a Gemini response into the KnowledgeContent shape.

    On any structural issue we degrade gracefully — the caller can decide
    whether to surface an error or serve the partial content.
    """
    if not raw:
        return {"theory": None, "examples": [], "interview_tips": [], "common_mistakes": [],
                "flashcards": [], "related_topics": [], "prerequisites": []}
    obj = parse_llm_json(raw)
    if obj is not None:
        return _normalize_shape(obj)
    return {"theory": None, "examples": [], "interview_tips": [], "common_mistakes": [],
            "flashcards": [], "related_topics": [], "prerequisites": [],
            "_parse_error": True, "_raw": raw[:400]}


def _as_list(v: Any) -> list:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        return [v]
    return []


def _normalize_shape(obj: dict) -> dict:
    """Coerce every section to the shape the frontend expects. Missing keys
    become empty lists / None so downstream rendering never blows up."""
    theory = obj.get("theory")
    if theory and not isinstance(theory, dict):
        theory = None
    return {
        "theory": theory,
        "examples": [e for e in _as_list(obj.get("examples")) if isinstance(e, dict)],
        "interview_tips": [str(t) for t in _as_list(obj.get("interview_tips")) if t],
        "common_mistakes": [m for m in _as_list(obj.get("common_mistakes")) if isinstance(m, dict)],
        "flashcards": [c for c in _as_list(obj.get("flashcards")) if isinstance(c, dict)],
        "related_topics": [r for r in _as_list(obj.get("related_topics")) if isinstance(r, dict)],
        "prerequisites": [p for p in _as_list(obj.get("prerequisites")) if isinstance(p, dict)],
    }
