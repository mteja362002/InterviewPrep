"""AI Gateway unit tests.

Tests cover the full gateway stack WITHOUT calling real LLMs:
  - Capability resolution
  - Provider routing / ordering
  - Retry logic with exponential backoff
  - Provider failover
  - No-providers-configured error
  - Error classification
  - Gemini adapter mocking
  - Gateway request / response lifecycle
  - Typed API (ai_service.complete)

All tests use mock adapters.  No network calls.  No API keys required.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Set
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# --- Gateway domain models --------------------------------------------------
from ai_gateway.models import (
    AICapability,
    AIProviderError,
    AIRequest,
    AIResponse,
    CapabilityProfile,
    ProviderDefinition,
    RetryPolicy,
    classify_error,
)
from ai_gateway.routing import (
    CapabilityRegistry,
    ProviderRegistry,
    RoutingPolicy,
)
from ai_gateway.gateway import Gateway


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeAdapter:
    """Minimal adapter that returns canned text or raises."""

    def __init__(self, response_text="Hello from fake", *, fail_n=0, error=None):
        self.response_text = response_text
        self.fail_n = fail_n        # fail this many times before succeeding
        self.error = error           # if set, always raise this
        self.call_count = 0

    async def complete(self, *, model, api_key, system_message, prompt,
                       temperature, max_tokens, timeout_seconds):
        self.call_count += 1
        if self.error:
            raise self.error
        if self.call_count <= self.fail_n:
            raise TimeoutError("simulated timeout")
        return self.response_text


def _make_provider(
    *,
    id="test-provider",
    priority=10,
    adapter=None,
    capabilities=None,
) -> ProviderDefinition:
    return ProviderDefinition(
        id=id,
        priority=priority,
        capabilities=capabilities or set(AICapability),
        model="test-model",
        api_key="test-key",
        adapter=adapter or _FakeAdapter(),
    )


def _make_request(capability=AICapability.KNOWLEDGE_GENERATION) -> AIRequest:
    return AIRequest(
        capability=capability,
        system_message="You are a test assistant.",
        prompt="Explain binary search.",
        session_id="test-session",
    )


# ===========================================================================
# 1. Capability Resolution
# ===========================================================================

class TestCapabilityRegistry:
    def test_all_default_capabilities_registered(self):
        registry = CapabilityRegistry()
        for cap in AICapability:
            assert registry.is_registered(cap), f"{cap.value} not registered"

    def test_resolve_returns_profile(self):
        registry = CapabilityRegistry()
        profile = registry.resolve(AICapability.KNOWLEDGE_GENERATION)
        assert isinstance(profile, CapabilityProfile)
        assert profile.temperature == 0.7
        assert profile.max_tokens == 8192

    def test_register_override(self):
        registry = CapabilityRegistry()
        custom = CapabilityProfile(
            temperature=0.1, max_tokens=100, timeout_seconds=5,
            retry_policy=RetryPolicy(max_retries=0),
        )
        registry.register(AICapability.KNOWLEDGE_GENERATION, custom)
        assert registry.resolve(AICapability.KNOWLEDGE_GENERATION) is custom

    def test_mentor_chat_vs_lesson_profiles_differ(self):
        registry = CapabilityRegistry()
        chat = registry.resolve(AICapability.MENTOR_CHAT)
        lesson = registry.resolve(AICapability.MENTOR_LESSON)
        # They share temperature but differ in structured_output
        assert lesson.structured_output is True
        assert chat.structured_output is False


# ===========================================================================
# 2. Provider Routing / Ordering
# ===========================================================================

class TestRoutingPolicy:
    def test_resolve_chain_orders_by_priority(self):
        registry = ProviderRegistry()
        registry.register(_make_provider(id="low", priority=20))
        registry.register(_make_provider(id="high", priority=5))
        registry.register(_make_provider(id="mid", priority=10))

        policy = RoutingPolicy()
        chain = policy.resolve_chain(AICapability.KNOWLEDGE_GENERATION, registry)
        assert [p.id for p in chain] == ["high", "mid", "low"]

    def test_resolve_chain_filters_by_capability(self):
        registry = ProviderRegistry()
        registry.register(_make_provider(
            id="full", priority=10,
            capabilities={AICapability.KNOWLEDGE_GENERATION, AICapability.MENTOR_CHAT},
        ))
        registry.register(_make_provider(
            id="limited", priority=5,
            capabilities={AICapability.MENTOR_CHAT},
        ))

        policy = RoutingPolicy()
        chain = policy.resolve_chain(AICapability.KNOWLEDGE_GENERATION, registry)
        assert len(chain) == 1
        assert chain[0].id == "full"

    def test_resolve_chain_empty_when_no_match(self):
        registry = ProviderRegistry()
        registry.register(_make_provider(
            id="chat-only", priority=10,
            capabilities={AICapability.MENTOR_CHAT},
        ))
        policy = RoutingPolicy()
        chain = policy.resolve_chain(AICapability.KNOWLEDGE_GENERATION, registry)
        assert chain == []

    def test_resolve_chain_skips_no_adapter(self):
        registry = ProviderRegistry()
        p = _make_provider(id="no-adapter", priority=1)
        p.adapter = None
        registry.register(p)
        policy = RoutingPolicy()
        chain = policy.resolve_chain(AICapability.KNOWLEDGE_GENERATION, registry)
        assert chain == []


# ===========================================================================
# 3. Provider Registry
# ===========================================================================

class TestProviderRegistry:
    def test_register_and_retrieve(self):
        registry = ProviderRegistry()
        p = _make_provider(id="test-1")
        registry.register(p)
        assert registry.count == 1
        assert registry.get_by_id("test-1") is p

    def test_get_all(self):
        registry = ProviderRegistry()
        registry.register(_make_provider(id="a"))
        registry.register(_make_provider(id="b"))
        assert len(registry.get_all()) == 2

    def test_get_by_id_missing(self):
        registry = ProviderRegistry()
        assert registry.get_by_id("nonexistent") is None

    def test_load_from_environment_no_keys(self):
        registry = ProviderRegistry()
        with patch.dict("os.environ", {}, clear=True):
            registry.load_from_environment()
        assert registry.count == 0

    def test_load_from_environment_with_gemini_key(self):
        registry = ProviderRegistry()
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key-123"}, clear=True):
            registry.load_from_environment()
        assert registry.count == 1
        assert registry.get_by_id("gemini-primary") is not None

    def test_load_from_environment_deduplicates_same_key(self):
        registry = ProviderRegistry()
        with patch.dict("os.environ", {
            "GEMINI_API_KEY": "same-key",
            "EMERGENT_LLM_KEY": "same-key",
        }, clear=True):
            registry.load_from_environment()
        # Same key → emergent fallback skipped
        assert registry.count == 1

    def test_load_from_environment_two_different_keys(self):
        registry = ProviderRegistry()
        with patch.dict("os.environ", {
            "GEMINI_API_KEY": "key-a",
            "EMERGENT_LLM_KEY": "key-b",
        }, clear=True):
            registry.load_from_environment()
        assert registry.count == 2


# ===========================================================================
# 4. Gateway Lifecycle
# ===========================================================================

class TestGatewayLifecycle:
    def test_complete_success(self):
        gw = Gateway()
        gw._provider_registry.register(
            _make_provider(adapter=_FakeAdapter("test response")),
        )
        gw._initialised = True

        request = _make_request()
        response = asyncio.run(gw.complete(request))
        assert isinstance(response, AIResponse)
        assert response.text == "test response"
        assert response.provider_used == "test-provider"
        assert response.capability == AICapability.KNOWLEDGE_GENERATION
        assert response.latency_ms >= 0

    def test_complete_no_providers_raises(self):
        gw = Gateway()
        gw._initialised = True  # skip env discovery

        request = _make_request()
        with pytest.raises(AIProviderError) as exc_info:
            asyncio.run(gw.complete(request))
        assert exc_info.value.kind == "no_providers"
        assert exc_info.value.status_code == 503

    def test_initialise_idempotent(self):
        gw = Gateway()
        with patch.object(gw._provider_registry, "load_from_environment") as mock:
            gw.initialise()
            gw.initialise()
            gw.initialise()
        assert mock.call_count == 1


# ===========================================================================
# 5. Retry Logic
# ===========================================================================

class TestRetryLogic:
    def test_retry_on_timeout(self):
        """Adapter fails once with timeout, succeeds on retry."""
        adapter = _FakeAdapter("retried OK", fail_n=1)
        gw = Gateway()
        gw._provider_registry.register(_make_provider(adapter=adapter))
        gw._initialised = True

        response = asyncio.run(gw.complete(_make_request()))
        assert response.text == "retried OK"
        assert adapter.call_count == 2  # 1 fail + 1 success

    def test_exhausts_retries(self):
        """Adapter always times out → raises after max retries."""
        adapter = _FakeAdapter(error=TimeoutError("always times out"))
        gw = Gateway()
        gw._provider_registry.register(_make_provider(adapter=adapter))
        gw._initialised = True

        with pytest.raises(AIProviderError) as exc_info:
            asyncio.run(gw.complete(_make_request()))
        # Single provider exhausted → gateway wraps as all_providers_failed
        assert exc_info.value.kind == "all_providers_failed"

    def test_non_retryable_error_skips_retry(self):
        """Auth errors are not retryable → immediate failure."""

        class AuthError(Exception):
            pass

        adapter = _FakeAdapter(error=AuthError("API key not valid"))
        gw = Gateway()
        gw._provider_registry.register(_make_provider(adapter=adapter))
        gw._initialised = True

        with pytest.raises(AIProviderError) as exc_info:
            asyncio.run(gw.complete(_make_request()))
        # Single provider fails → gateway wraps as all_providers_failed
        assert exc_info.value.kind == "all_providers_failed"
        assert adapter.call_count == 1  # no retries


# ===========================================================================
# 6. Provider Failover
# ===========================================================================

class TestProviderFailover:
    def test_failover_to_second_provider(self):
        """First provider always fails → gateway falls over to second."""
        primary = _FakeAdapter(error=TimeoutError("primary down"))
        fallback = _FakeAdapter("fallback response")

        gw = Gateway()
        gw._provider_registry.register(
            _make_provider(id="primary", priority=10, adapter=primary),
        )
        gw._provider_registry.register(
            _make_provider(id="fallback", priority=20, adapter=fallback),
        )
        gw._initialised = True

        response = asyncio.run(gw.complete(_make_request()))
        assert response.text == "fallback response"
        assert response.provider_used == "fallback"

    def test_all_providers_exhausted(self):
        """Both providers fail → raises all_providers_failed."""
        gw = Gateway()
        gw._provider_registry.register(
            _make_provider(id="a", priority=10, adapter=_FakeAdapter(error=TimeoutError("a fail"))),
        )
        gw._provider_registry.register(
            _make_provider(id="b", priority=20, adapter=_FakeAdapter(error=TimeoutError("b fail"))),
        )
        gw._initialised = True

        with pytest.raises(AIProviderError) as exc_info:
            asyncio.run(gw.complete(_make_request()))
        assert exc_info.value.kind == "all_providers_failed"
        assert exc_info.value.status_code == 503


# ===========================================================================
# 7. Error Classification
# ===========================================================================

class TestErrorClassification:
    @pytest.mark.parametrize("msg,expected_kind", [
        ("API key not valid", "invalid_key"),
        ("api_key_invalid: check your credentials", "invalid_key"),
        ("Unauthorized access", "invalid_key"),
        ("Permission denied for this resource", "invalid_key"),
        ("Error 401: invalid credentials", "invalid_key"),
    ])
    def test_invalid_key_patterns(self, msg, expected_kind):
        err = classify_error(Exception(msg))
        assert err.kind == expected_kind

    @pytest.mark.parametrize("msg,expected_kind", [
        ("Rate limit exceeded", "rate_limit"),
        ("Quota exhausted for today", "rate_limit"),
        ("Too many requests", "rate_limit"),
        ("Resource exhausted", "rate_limit"),
        ("Error 429", "rate_limit"),
    ])
    def test_rate_limit_patterns(self, msg, expected_kind):
        err = classify_error(Exception(msg))
        assert err.kind == expected_kind

    @pytest.mark.parametrize("msg,expected_kind", [
        ("Model not found: gemini-1.5-flash", "model_not_found"),
        ("Invalid model name specified", "model_not_found"),
        ("Unknown model: gpt-99", "model_not_found"),
        ("NotFoundError: model does not exist", "model_not_found"),
    ])
    def test_model_not_found_patterns(self, msg, expected_kind):
        err = classify_error(Exception(msg))
        assert err.kind == expected_kind

    @pytest.mark.parametrize("msg,expected_kind", [
        ("Request timeout after 30s", "timeout"),
        ("Read timed out after 30s", "timeout"),
    ])
    def test_timeout_patterns(self, msg, expected_kind):
        err = classify_error(Exception(msg))
        assert err.kind == expected_kind

    @pytest.mark.parametrize("msg,expected_kind", [
        ("Connection refused", "upstream"),
        ("Service unavailable", "upstream"),
        ("Error 503: backend down", "upstream"),
        ("Name resolution failed", "upstream"),
    ])
    def test_network_patterns(self, msg, expected_kind):
        err = classify_error(Exception(msg))
        assert err.kind == expected_kind

    def test_unknown_error_fallback(self):
        err = classify_error(Exception("something completely unexpected"))
        assert err.kind == "unknown"
        assert err.status_code == 502

    def test_classify_by_class_name(self):
        """Fast path: classify by exception class name."""
        class RateLimitError(Exception):
            pass
        err = classify_error(RateLimitError("too fast"))
        assert err.kind == "rate_limit"

    def test_provider_error_attributes(self):
        err = AIProviderError("test msg", kind="test_kind", status_code=418)
        assert str(err) == "test msg"
        assert err.kind == "test_kind"
        assert err.status_code == 418


# ===========================================================================
# 8. Typed API (ai_service.complete)
# ===========================================================================

class TestTypedAPI:
    def test_complete_delegates_to_gateway(self):
        from ai_service import complete, AICapability, AIProviderError

        mock_gw = MagicMock()
        mock_gw.complete = AsyncMock(return_value=AIResponse(
            text="gateway response",
            provider_used="mock",
            model_used="mock-model",
            latency_ms=42,
            capability=AICapability.KNOWLEDGE_GENERATION,
        ))

        with patch("ai_service.get_gateway", return_value=mock_gw):
            result = asyncio.run(complete(
                capability=AICapability.KNOWLEDGE_GENERATION,
                system_message="test",
                prompt="test prompt",
                session_id="test",
            ))
        assert result == "gateway response"
        mock_gw.complete.assert_awaited_once()

    def test_complete_empty_prompt_raises(self):
        from ai_service import complete, AICapability, AIProviderError

        with pytest.raises(AIProviderError) as exc_info:
            asyncio.run(complete(
                capability=AICapability.KNOWLEDGE_GENERATION,
                system_message="test",
                prompt="   ",
            ))
        assert exc_info.value.kind == "invalid_request"
        assert exc_info.value.status_code == 400

    def test_complete_json_removed(self):
        """Verify complete_json is no longer importable."""
        import ai_service
        assert not hasattr(ai_service, "complete_json"), \
            "complete_json should have been removed in Sprint 5"

    def test_all_exports(self):
        """__all__ contains exactly the expected symbols."""
        import ai_service
        assert set(ai_service.__all__) == {"AICapability", "AIProviderError", "complete"}


# ===========================================================================
# 9. Response Pipeline
# ===========================================================================

class TestResponsePipeline:
    def test_response_contains_metadata(self):
        gw = Gateway()
        adapter = _FakeAdapter("response text")
        gw._provider_registry.register(
            _make_provider(id="meta-test", adapter=adapter),
        )
        gw._initialised = True

        response = asyncio.run(gw.complete(_make_request()))
        assert response.text == "response text"
        assert response.provider_used == "meta-test"
        assert response.model_used == "test-model"
        assert response.capability == AICapability.KNOWLEDGE_GENERATION
        assert isinstance(response.latency_ms, int)


# ===========================================================================
# 10. Request Pipeline
# ===========================================================================

class TestRequestPipeline:
    def test_request_passes_through(self):
        """v1 request pipeline is a pass-through."""
        gw = Gateway()
        request = _make_request()
        result = gw._request_pipeline(request)
        assert result is request
