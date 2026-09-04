"""AI Gateway core.

The gateway is the single orchestrator for all AI completions.  It owns:

    - Request pipeline   (v1: pass-through, future: validation / truncation)
    - Capability resolution via ``CapabilityRegistry``
    - Provider chain resolution via ``RoutingPolicy``
    - Execution loop with simple failover (retry + next-provider)
    - Response pipeline   (v1: wrap raw text, future: parsing / normalisation)
    - Structured logging for telemetry

The gateway is instantiated once at module load (see ``__init__.py``)
and is called exclusively via ``ai_service.complete()``.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import List

from ai_gateway.models import (
    AICapability,
    AIProviderError,
    AIRequest,
    AIResponse,
    CapabilityProfile,
    ProviderDefinition,
    classify_error,
)
from ai_gateway.routing import (
    CapabilityRegistry,
    ProviderRegistry,
    RoutingPolicy,
)
from ai_gateway.providers import discover

log = logging.getLogger(__name__)


class Gateway:
    """Centralised AI Gateway.

    Call ``complete()`` with an ``AIRequest`` to execute an AI completion
    through the provider chain with automatic failover.
    """

    def __init__(self) -> None:
        self._capability_registry = CapabilityRegistry()
        self._provider_registry = ProviderRegistry()
        self._routing_policy = RoutingPolicy()
        self._initialised = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialise(self) -> None:
        """Discover providers from environment and populate registries.

        Called once at startup.  Safe to call multiple times (idempotent
        after first call).
        """
        if self._initialised:
            return

        for defn in discover():
            self._provider_registry.register(defn)

        self._initialised = True
        log.info(
            "AI Gateway initialised — %d provider(s) registered",
            self._provider_registry.count,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def complete(self, request: AIRequest) -> AIResponse:
        """Execute an AI completion through the provider chain.

        1. **Request pipeline** — v1 pass-through.
        2. **Resolve capability** → ``CapabilityProfile``.
        3. **Resolve provider chain** → ordered ``List[ProviderDefinition]``.
        4. **Execution loop** — try each provider with retries.
        5. **Response pipeline** — wrap raw text into ``AIResponse``.

        Raises ``AIProviderError`` only when every provider has been
        exhausted.
        """
        self.initialise()

        # 1. Request pipeline (extension point — v1 is a no-op)
        request = self._request_pipeline(request)

        # 2. Resolve capability
        profile = self._capability_registry.resolve(request.capability)

        # 3. Resolve provider chain
        chain = self._routing_policy.resolve_chain(
            request.capability,
            self._provider_registry,
        )

        if not chain:
            raise AIProviderError(
                "No AI providers are configured. Please contact support.",
                kind="no_providers",
                status_code=503,
            )

        # 4. Execution loop with failover
        last_error: AIProviderError | None = None
        start = time.monotonic()

        for provider in chain:
            try:
                raw_text = await self._execute_with_provider(
                    provider, request, profile,
                )

                # 5. Response pipeline
                latency_ms = int((time.monotonic() - start) * 1000)
                response = self._response_pipeline(
                    raw_text=raw_text,
                    provider=provider,
                    request=request,
                    latency_ms=latency_ms,
                )
                self._log_success(request, provider, latency_ms)
                return response

            except AIProviderError as err:
                last_error = err
                log.warning(
                    "Provider %s failed (kind=%s) — trying next",
                    provider.id, err.kind,
                )
                continue

        # All providers exhausted
        self._log_failure(request, last_error)
        raise AIProviderError(
            "AI is temporarily unavailable. Please try again shortly.",
            kind="all_providers_failed",
            status_code=503,
        )

    # ------------------------------------------------------------------
    # Execution (per-provider, with retry)
    # ------------------------------------------------------------------

    async def _execute_with_provider(
        self,
        provider: ProviderDefinition,
        request: AIRequest,
        profile: CapabilityProfile,
    ) -> str:
        """Try a single provider with the capability's retry policy.

        Returns raw text on success.  Raises ``AIProviderError`` when
        the provider is exhausted (all retries failed or non-retryable error).
        """
        retry = profile.retry_policy
        last_error: AIProviderError | None = None

        for attempt in range(retry.max_retries + 1):
            try:
                raw_text = await provider.adapter.complete(
                    model=provider.model,
                    api_key=provider.api_key,
                    system_message=request.system_message,
                    prompt=request.prompt,
                    temperature=profile.temperature,
                    max_tokens=profile.max_tokens,
                    timeout_seconds=profile.timeout_seconds,
                )
                return raw_text

            except AIProviderError:
                raise   # already classified — re-raise directly
            except Exception as exc:
                classified = classify_error(exc)
                last_error = classified

                # Non-retryable? Stop immediately.
                if classified.kind not in retry.retryable_kinds:
                    raise classified

                # Retryable but last attempt? Give up on this provider.
                if attempt >= retry.max_retries:
                    raise classified

                # Wait with exponential backoff + jitter before retrying.
                delay = retry.base_delay_seconds * (2 ** attempt)
                delay += random.uniform(0, 0.5)
                log.info(
                    "Retrying provider %s (attempt %d/%d, delay=%.1fs, kind=%s)",
                    provider.id, attempt + 1, retry.max_retries,
                    delay, classified.kind,
                )
                await asyncio.sleep(delay)

        # Should not reach here, but guard defensively.
        raise last_error or AIProviderError(
            "Provider exhausted after retries.",
            kind="unknown", status_code=502,
        )

    # ------------------------------------------------------------------
    # Pipelines (extension points)
    # ------------------------------------------------------------------

    def _request_pipeline(self, request: AIRequest) -> AIRequest:
        """Pre-process a request before routing.

        v1: pass-through.  Future extensions:
            - token estimation
            - prompt validation / truncation
            - safety filtering
        """
        return request

    def _response_pipeline(
        self,
        *,
        raw_text: str,
        provider: ProviderDefinition,
        request: AIRequest,
        latency_ms: int,
    ) -> AIResponse:
        """Post-process a provider response.

        v1: wraps raw text into ``AIResponse`` with metadata.
        Future extensions:
            - JSON validation (for structured_output capabilities)
            - markdown cleanup
            - output normalisation
        """
        return AIResponse(
            text=raw_text,
            provider_used=provider.id,
            model_used=provider.model,
            latency_ms=latency_ms,
            capability=request.capability,
        )

    # ------------------------------------------------------------------
    # Telemetry (structured logging — v1)
    # ------------------------------------------------------------------

    def _log_success(
        self,
        request: AIRequest,
        provider: ProviderDefinition,
        latency_ms: int,
    ) -> None:
        log.info(
            "ai_gateway.complete OK · capability=%s · provider=%s · "
            "model=%s · latency=%dms · session=%s",
            request.capability.value, provider.id,
            provider.model, latency_ms, request.session_id,
        )

    def _log_failure(
        self,
        request: AIRequest,
        last_error: AIProviderError | None,
    ) -> None:
        log.error(
            "ai_gateway.complete FAILED · capability=%s · "
            "all_providers_exhausted · last_kind=%s · session=%s",
            request.capability.value,
            last_error.kind if last_error else "unknown",
            request.session_id,
        )
