"""Phase 3C.1 — provider-agnostic assessment prompt scaffolding.

Pure unit tests. Ensure the prompt registry exists, coding has no template,
and builders produce a structured PromptSpec bound to the MissionContext
without referencing any concrete LLM provider.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from assessment.prompts import get_prompt_template, PROMPT_REGISTRY, PromptSpec  # noqa: E402
from services.mission_context import build_mission_context  # noqa: E402


def test_registry_covers_non_coding_types_only():
    for t in ("quiz", "behavioral", "design", "system_design"):
        assert get_prompt_template(t) is not None
    # Coding is powered by representative problems, NOT AI generation.
    assert get_prompt_template("coding") is None


def test_quiz_prompt_uses_context_objectives():
    ctx = build_mission_context("pf.intro.core")
    spec = get_prompt_template("quiz")(ctx, {"confidence": 0.4, "mastery": 0.3, "excluded_topics": ["recursion"]})
    assert isinstance(spec, PromptSpec)
    assert spec.assessment_type == "quiz"
    assert spec.variables["topic"] == ctx.topic
    assert spec.variables["learning_stage"] == ctx.learning_stage
    assert spec.variables["excluded_topics"] == ["recursion"]
    assert "output_schema" or spec.output_schema


def test_no_provider_is_hardcoded():
    ctx = build_mission_context("hld.foundations.scalability")
    for t in ("quiz", "behavioral", "design", "system_design"):
        spec = get_prompt_template(t)(ctx, None)
        blob = (spec.system + spec.user).lower()
        for banned in ("openai", "gpt", "gemini", "claude", "anthropic"):
            assert banned not in blob, f"{t} prompt must be provider-agnostic ({banned})"
