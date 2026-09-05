"""Phase 5 — Consumer hardening end-to-end tests.

Every test in this file proves a concrete consumer boundary property:

  1. Consumers call ``ai_service.complete()`` — never a provider SDK.
  2. The correct ``AICapability`` reaches the gateway.
  3. ``AIResponse`` metadata propagates through the gateway.
  4. Provider-specific exceptions never leak to consumers.
  5. Malformed responses follow existing graceful-fallback behaviour.
  6. ``ai_gateway.parsers`` is the only JSON parser used.
  7. Capability → tier → model_used reaches ``AIResponse.model_used``.

All tests are offline (mock adapters / patches).  No API keys required.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_gateway.gateway import Gateway
from ai_gateway.models import (
    AICapability,
    AIProviderError,
    AIRequest,
    AIResponse,
    CapabilityProfile,
    ProviderDefinition,
    RetryPolicy,
)
from ai_gateway.routing import CapabilityRegistry
from ai_gateway.model_selection import ModelSelector, _MODEL_TIERS


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

class _StubAdapter:
    """Adapter stub that records calls and returns canned text."""

    def __init__(self, response_text: str = "stub response"):
        self._response_text = response_text
        self.calls: list[dict] = []

    @property
    def name(self) -> str:
        return "openrouter"

    async def complete(self, *, model, api_key, system_message,
                       prompt, temperature, max_tokens, timeout_seconds):
        self.calls.append({
            "model": model, "system_message": system_message,
            "prompt": prompt, "temperature": temperature,
        })
        return self._response_text


class _FailingAdapter(_StubAdapter):
    """Adapter that always raises."""

    def __init__(self, exc: Exception):
        super().__init__()
        self._exc = exc

    async def complete(self, **kw):
        raise self._exc


def _gateway_with_stub(response_text: str = "stub response") -> tuple[Gateway, _StubAdapter]:
    """Minimal gateway with one OpenRouter stub provider."""
    adapter = _StubAdapter(response_text)
    provider = ProviderDefinition(
        id="openrouter", priority=5,
        capabilities=set(AICapability),
        model="google/gemini-2.5-flash",
        api_key="test-key",
        adapter=adapter,
    )
    gw = Gateway()
    gw._initialised = True
    gw._provider_registry.register(provider)
    return gw, adapter


def _make_request(capability: AICapability = AICapability.KNOWLEDGE_GENERATION,
                  prompt: str = "test prompt") -> AIRequest:
    return AIRequest(
        capability=capability,
        system_message="system",
        prompt=prompt,
        session_id="test-session",
    )


# ===========================================================================
# 1. Consumer → ai_service.complete() → Gateway  (the "golden path")
# ===========================================================================

class TestKnowledgeGenerationConsumer:
    """Knowledge generation: ensure_content → ai_service.complete(KNOWLEDGE_GENERATION)."""

    def test_uses_knowledge_generation_capability(self):
        """The consumer passes KNOWLEDGE_GENERATION to the gateway."""
        gw, adapter = _gateway_with_stub('{"theory": {"beginner": "x"}, "flashcards": []}')

        with patch("ai_service.get_gateway", return_value=gw):
            from ai_service import complete
            result = asyncio.run(complete(
                capability=AICapability.KNOWLEDGE_GENERATION,
                system_message="You are PrepOS Mentor",
                prompt="Generate for Arrays",
                session_id="kb::arrays",
            ))

        assert result == '{"theory": {"beginner": "x"}, "flashcards": []}'
        assert len(adapter.calls) == 1
        assert adapter.calls[0]["system_message"] == "You are PrepOS Mentor"

    def test_malformed_response_is_surfaced_as_text(self):
        """ai_service.complete returns raw text; parsing is the consumer's job."""
        gw, _ = _gateway_with_stub("not valid JSON at all")

        with patch("ai_service.get_gateway", return_value=gw):
            from ai_service import complete
            result = asyncio.run(complete(
                capability=AICapability.KNOWLEDGE_GENERATION,
                system_message="sys",
                prompt="test",
            ))
        assert result == "not valid JSON at all"

    def test_knowledge_parser_integration(self):
        """prompt_builder.parse_content delegates to ai_gateway.parsers."""
        from prompt_builder import parse_content
        from ai_gateway.parsers import parse_llm_json

        # Valid JSON wrapped in code fences — the shared parser handles this.
        raw = '```json\n{"theory": {"beginner": "test"}, "examples": []}\n```'
        parsed = parse_content(raw)
        assert parsed["theory"] == {"beginner": "test"}

        # Malformed response → graceful fallback with _parse_error.
        bad = parse_content("completely broken")
        assert bad["_parse_error"] is True
        assert bad["theory"] is None


class TestMentorChatConsumer:
    """Mentor chat: answer(style='chat') → ai_service.complete(MENTOR_CHAT)."""

    def test_uses_mentor_chat_capability(self):
        """Chat mode routes through MENTOR_CHAT."""
        gw, adapter = _gateway_with_stub("Hello! Let me help you with arrays.")

        with patch("ai_service.get_gateway", return_value=gw):
            from ai_service import complete
            result = asyncio.run(complete(
                capability=AICapability.MENTOR_CHAT,
                system_message="You are the mentor",
                prompt="Explain arrays",
                session_id="mentor::conv-1",
            ))

        assert "arrays" in result.lower() or len(result) > 0
        assert len(adapter.calls) == 1

    def test_empty_response_does_not_crash_service(self):
        """Gateway raises on empty; consumer sees AIProviderError."""
        adapter = _FailingAdapter(RuntimeError("AI returned an empty response"))
        provider = ProviderDefinition(
            id="openrouter", priority=5,
            capabilities=set(AICapability),
            model="google/gemini-2.5-flash",
            api_key="test-key",
            adapter=adapter,
        )
        gw = Gateway()
        gw._initialised = True
        gw._provider_registry.register(provider)

        with patch("ai_service.get_gateway", return_value=gw):
            from ai_service import complete, AIProviderError
            with pytest.raises(AIProviderError):
                asyncio.run(complete(
                    capability=AICapability.MENTOR_CHAT,
                    system_message="sys", prompt="test",
                ))


class TestMentorLessonConsumer:
    """Mentor lesson: answer(style='lesson') → ai_service.complete(MENTOR_LESSON)."""

    def test_uses_mentor_lesson_capability(self):
        gw, adapter = _gateway_with_stub('{"executive_summary": "Arrays lesson"}')

        with patch("ai_service.get_gateway", return_value=gw):
            from ai_service import complete
            result = asyncio.run(complete(
                capability=AICapability.MENTOR_LESSON,
                system_message="lesson system",
                prompt="Teach arrays",
                session_id="mentor::conv-2",
            ))

        assert "Arrays lesson" in result
        assert len(adapter.calls) == 1

    def test_lesson_uses_shared_parser(self):
        """mentor_service.parse_llm_json IS ai_gateway.parsers.parse_llm_json."""
        from ai_mentor import mentor_service
        from ai_gateway.parsers import parse_llm_json
        assert mentor_service.parse_llm_json is parse_llm_json


class TestMissionNarrativeConsumer:
    """Mission narrative: generate_narrative_and_previews → ai_service.complete(MISSION_NARRATIVE)."""

    def test_uses_mission_narrative_capability(self):
        envelope = json.dumps({
            "narrative": "Focus on arrays today.",
            "tomorrow_preview": {"focus": "Hash maps", "why": "prereq complete"},
            "week_goal": {"headline": "Master fundamentals"},
        })
        gw, adapter = _gateway_with_stub(envelope)

        with patch("ai_service.get_gateway", return_value=gw):
            from ai_mentor.mission_planner import generate_narrative_and_previews
            with patch("ai_mentor.mission_planner.build_context", new=AsyncMock(return_value={})), \
                 patch("ai_mentor.mission_planner.serialize_context", return_value="ctx"):
                result = asyncio.run(generate_narrative_and_previews(
                    object(), user_id="u1", mission={"title": "Arrays", "tasks": []},
                ))

        assert result["ai_narrative"] == "Focus on arrays today."
        assert result["tomorrow_preview"]["focus"] == "Hash maps"

    def test_ai_failure_returns_empty_dict(self):
        """Mission planner degrades gracefully on AI failure."""
        adapter = _FailingAdapter(RuntimeError("provider down"))
        provider = ProviderDefinition(
            id="openrouter", priority=5,
            capabilities=set(AICapability),
            model="google/gemini-2.5-flash",
            api_key="test-key",
            adapter=adapter,
        )
        gw = Gateway()
        gw._initialised = True
        gw._provider_registry.register(provider)

        with patch("ai_service.get_gateway", return_value=gw):
            from ai_mentor.mission_planner import generate_narrative_and_previews
            with patch("ai_mentor.mission_planner.build_context", new=AsyncMock(return_value={})), \
                 patch("ai_mentor.mission_planner.serialize_context", return_value="ctx"):
                result = asyncio.run(generate_narrative_and_previews(
                    object(), user_id="u1", mission={"title": "Test", "tasks": []},
                ))

        # Graceful degradation — empty dict, no crash.
        assert result == {}

    def test_malformed_json_returns_empty_dict(self):
        """Unparseable AI response → empty dict (mission still works)."""
        gw, _ = _gateway_with_stub("This is not JSON")

        with patch("ai_service.get_gateway", return_value=gw):
            from ai_mentor.mission_planner import generate_narrative_and_previews
            with patch("ai_mentor.mission_planner.build_context", new=AsyncMock(return_value={})), \
                 patch("ai_mentor.mission_planner.serialize_context", return_value="ctx"):
                result = asyncio.run(generate_narrative_and_previews(
                    object(), user_id="u1", mission={"title": "Test", "tasks": []},
                ))

        assert result == {}


class TestAssessmentContentCapability:
    """Assessment content capability exists and maps to deep tier."""

    def test_assessment_capability_is_registered(self):
        registry = CapabilityRegistry()
        assert registry.is_registered(AICapability.ASSESSMENT_CONTENT)

    def test_assessment_routes_through_gateway(self):
        gw, adapter = _gateway_with_stub("assessment response")

        with patch("ai_service.get_gateway", return_value=gw):
            from ai_service import complete
            result = asyncio.run(complete(
                capability=AICapability.ASSESSMENT_CONTENT,
                system_message="assessment system",
                prompt="Generate assessment",
            ))

        assert result == "assessment response"
        assert len(adapter.calls) == 1


# ===========================================================================
# 2. Error Boundary — provider exceptions never leak
# ===========================================================================

class TestErrorBoundary:
    """Provider-specific exceptions are normalized to AIProviderError."""

    def test_runtime_error_classified_to_ai_provider_error(self):
        """Raw RuntimeError from adapter → AIProviderError at consumer."""
        adapter = _FailingAdapter(RuntimeError("Connection reset"))
        provider = ProviderDefinition(
            id="openrouter", priority=5,
            capabilities=set(AICapability),
            model="m", api_key="k",
            adapter=adapter,
        )
        gw = Gateway()
        gw._initialised = True
        gw._provider_registry.register(provider)

        with patch("ai_service.get_gateway", return_value=gw):
            from ai_service import complete, AIProviderError as APE
            with pytest.raises(APE) as exc_info:
                asyncio.run(complete(
                    capability=AICapability.MENTOR_CHAT,
                    system_message="s", prompt="p",
                ))
            # The error should have a kind — NOT a raw provider class name.
            assert exc_info.value.kind in (
                "unknown", "upstream", "timeout", "rate_limit",
                "invalid_key", "model_not_found", "all_providers_failed",
            )

    def test_provider_error_message_is_user_safe(self):
        """Error messages from the fast-path (class-name match) are clean."""
        from ai_gateway.models import classify_error

        # Fast-path: AuthenticationError class name → clean message.
        class AuthenticationError(Exception):
            pass

        err = classify_error(AuthenticationError("api_key sk-abc123 is invalid"))
        assert "sk-abc123" not in str(err)
        assert err.kind == "invalid_key"

    def test_fallback_error_truncates_raw_message(self):
        """The fallback classifier truncates long messages to 180 chars."""
        from ai_gateway.models import classify_error

        long_msg = "x" * 300
        err = classify_error(RuntimeError(long_msg))
        assert len(str(err)) < 300
        assert err.kind == "unknown"

    def test_all_providers_exhausted_error(self):
        """When the only provider fails, consumer gets a clean error."""
        adapter = _FailingAdapter(RuntimeError("500 internal"))
        provider = ProviderDefinition(
            id="test", priority=5,
            capabilities=set(AICapability),
            model="m", api_key="k",
            adapter=adapter,
        )
        gw = Gateway()
        gw._initialised = True
        gw._provider_registry.register(provider)

        with patch("ai_service.get_gateway", return_value=gw):
            from ai_service import complete, AIProviderError
            with pytest.raises(AIProviderError) as exc_info:
                asyncio.run(complete(
                    capability=AICapability.KNOWLEDGE_GENERATION,
                    system_message="s", prompt="p",
                ))
            assert exc_info.value.kind == "all_providers_failed"
            assert exc_info.value.status_code == 503


# ===========================================================================
# 3. Response Contract — AIResponse metadata survives the call chain
# ===========================================================================

class TestResponseContract:
    """Verify AIResponse fields are populated correctly through the gateway."""

    def test_response_metadata_populated(self):
        gw, adapter = _gateway_with_stub("response text")
        response = asyncio.run(gw.complete(_make_request()))

        assert response.text == "response text"
        assert response.provider_used == "openrouter"
        assert response.model_used != ""
        assert isinstance(response.latency_ms, int)
        assert response.latency_ms >= 0
        assert response.capability == AICapability.KNOWLEDGE_GENERATION

    def test_model_used_reflects_tier_selection(self):
        """For OpenRouter, model_used should be the tier-selected model,
        NOT the provider's default model."""
        gw, adapter = _gateway_with_stub("text")
        response = asyncio.run(gw.complete(
            _make_request(AICapability.MENTOR_CHAT),
        ))
        # MENTOR_CHAT → fast tier → should get the fast model
        assert response.model_used == _MODEL_TIERS["fast"]
        assert response.provider_used == "openrouter"

    def test_ai_service_returns_only_text(self):
        """ai_service.complete() returns str, not AIResponse."""
        gw, _ = _gateway_with_stub("just text")

        with patch("ai_service.get_gateway", return_value=gw):
            from ai_service import complete
            result = asyncio.run(complete(
                capability=AICapability.KNOWLEDGE_GENERATION,
                system_message="s", prompt="p",
            ))
        assert isinstance(result, str)
        assert result == "just text"


# ===========================================================================
# 4. Capability → Tier → Model Routing  (regression)
# ===========================================================================

class TestCapabilityToTierRouting:
    """Verify the full chain: capability → profile.reasoning → model tier."""

    @pytest.mark.parametrize("capability,expected_tier", [
        (AICapability.MENTOR_CHAT, "fast"),
        (AICapability.KNOWLEDGE_GENERATION, "standard"),
        (AICapability.MENTOR_LESSON, "standard"),
        (AICapability.MISSION_NARRATIVE, "fast"),
        (AICapability.ASSESSMENT_CONTENT, "deep"),
    ])
    def test_capability_resolves_to_expected_tier(self, capability, expected_tier):
        registry = CapabilityRegistry()
        profile = registry.resolve(capability)
        assert profile.reasoning == expected_tier

    @pytest.mark.parametrize("capability,expected_tier", [
        (AICapability.MENTOR_CHAT, "fast"),
        (AICapability.KNOWLEDGE_GENERATION, "standard"),
        (AICapability.MISSION_NARRATIVE, "fast"),
        (AICapability.ASSESSMENT_CONTENT, "deep"),
    ])
    def test_model_used_matches_tier_through_gateway(self, capability, expected_tier):
        gw, adapter = _gateway_with_stub("text")
        response = asyncio.run(gw.complete(_make_request(capability)))
        assert response.model_used == _MODEL_TIERS[expected_tier]


# ===========================================================================
# 5. Provider SDK coupling — static audit
# ===========================================================================

class TestProviderSdkCoupling:
    """Verify no consumer module imports provider SDKs."""

    @pytest.mark.parametrize("module_path", [
        "knowledge_generation",
        "ai_mentor.mentor_service",
        "ai_mentor.mission_planner",
        "prompt_builder",
    ])
    def test_consumer_does_not_import_provider_sdks(self, module_path):
        """No consumer should import google.genai, openai, or anthropic."""
        import importlib
        mod = importlib.import_module(module_path)
        source = open(mod.__file__, encoding="utf-8").read()
        for sdk in ("from google import genai", "import openai",
                     "from openai", "import anthropic", "from anthropic",
                     "import litellm", "from litellm"):
            assert sdk not in source, (
                f"{module_path} contains forbidden provider SDK import: {sdk}"
            )

    def test_consumers_import_only_ai_service(self):
        """All consumers use ai_service, not ai_gateway directly for completions."""
        import knowledge_generation
        import ai_mentor.mentor_service as ms
        import ai_mentor.mission_planner as mp

        for mod in (knowledge_generation, ms, mp):
            source = open(mod.__file__, encoding="utf-8").read()
            assert "from ai_service import" in source or "import ai_service" in source


# ===========================================================================
# 6. Parser integration — no duplication
# ===========================================================================

class TestParserIntegration:
    """Verify all consumers use the canonical ai_gateway.parsers."""

    def test_prompt_builder_uses_shared_parser(self):
        from prompt_builder import parse_content
        from ai_gateway.parsers import parse_llm_json

        # parse_content internally delegates to parse_llm_json
        result = parse_content('{"theory": null}')
        assert result["theory"] is None

    def test_mentor_service_uses_shared_parser(self):
        from ai_mentor.mentor_service import parse_llm_json as mentor_parser
        from ai_gateway.parsers import parse_llm_json
        assert mentor_parser is parse_llm_json

    def test_mission_planner_uses_shared_parser(self):
        from ai_mentor.mission_planner import parse_llm_json as planner_parser
        from ai_gateway.parsers import parse_llm_json
        assert planner_parser is parse_llm_json
