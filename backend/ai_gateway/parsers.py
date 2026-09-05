"""Shared JSON parsing utilities for LLM responses.

LLMs frequently wrap valid JSON in markdown code fences, add commentary
before/after the JSON, or produce slightly malformed output.  This module
provides a single, battle-tested parser pipeline that every consumer can
reuse — eliminating the three duplicate implementations previously
scattered across ``prompt_builder``, ``mentor_service``, and
``mission_planner``.

Usage::

    from ai_gateway.parsers import parse_llm_json

    obj = parse_llm_json(raw_llm_text)
    if obj is None:
        # all parse strategies failed
        ...
"""
from __future__ import annotations

import json
import re
from typing import Optional

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def strip_code_fence(text: str) -> str:
    """Remove leading/trailing markdown code fences.

    Handles ````` `` ` ````, ````` `` `json ````, and stray trailing fences.
    """
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, count=1)
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def extract_first_json_object(text: str) -> str:
    """Return the first balanced ``{...}`` slice — a last-resort recovery.

    If no opening brace is found, returns the input unchanged.
    """
    start = text.find("{")
    if start == -1:
        return text
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    # Unclosed — return from first brace to end.
    return text[start:]


def parse_llm_json(text: str) -> Optional[dict]:
    """Best-effort JSON parse from raw LLM output.

    Attempts, in order:
        1. Direct ``json.loads``.
        2. Strip code fence, then ``json.loads``.
        3. Regex-extract from a fenced block.
        4. Extract first balanced ``{…}`` object.

    Returns ``None`` if all strategies fail.
    """
    if not text:
        return None

    # 1. Direct parse.
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # 2. Strip code fence.
    cleaned = strip_code_fence(text)
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # 3. Regex-extract from a fenced block.
    m = _CODE_FENCE_RE.search(text)
    if m:
        try:
            obj = json.loads(m.group(1))
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    # 4. First balanced {…}.
    first_obj = extract_first_json_object(cleaned)
    if first_obj != cleaned:
        try:
            obj = json.loads(first_obj)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    return None
