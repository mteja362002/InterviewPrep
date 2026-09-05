"""Capability registry, provider registry, and routing policy.

Three distinct responsibilities in one cohesive module:

``CapabilityRegistry``
    Owns capability → profile mapping.  Validates capability names and
    returns ``CapabilityProfile`` instances.  Consumer code must never
    access capability profiles directly.

``ProviderRegistry``
    Knows **which** providers are available.  Stores ``ProviderDefinition``
    entries discovered at startup.  Owns environment-variable discovery
    and adapter instantiation via ``load_from_environment()``.
    Does NOT make routing decisions.

``RoutingPolicy``
    Decides **which** provider to try and in **what order**.  Consults
    the provider registry, filters by capability support, and orders by
    priority.  Owns all future routing strategies (latency-based,
    cost-based, round-robin).
"""
from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional

from ai_gateway.models import (
    AICapability,
    AIProviderError,
    CapabilityProfile,
    ProviderDefinition,
    RetryPolicy,
)

logger = logging.getLogger(__name__)


# ===========================================================================
# Capability Registry
# ===========================================================================

# Default profiles — centralised, never in consumer code.
_DEFAULT_PROFILES: Dict[AICapability, CapabilityProfile] = {
    AICapability.KNOWLEDGE_GENERATION: CapabilityProfile(
        temperature=0.7,
        max_tokens=8192,
        timeout_seconds=30,
        retry_policy=RetryPolicy(max_retries=2),
        structured_output=True,
        reasoning="standard",
        cost_priority="balanced",
    ),
    AICapability.MENTOR_CHAT: CapabilityProfile(
        temperature=0.6,
        max_tokens=4096,
        timeout_seconds=30,
        retry_policy=RetryPolicy(max_retries=2),
        reasoning="fast",
        latency_priority="low",
        cost_priority="economy",
    ),
    AICapability.MENTOR_LESSON: CapabilityProfile(
        temperature=0.6,
        max_tokens=4096,
        timeout_seconds=30,
        retry_policy=RetryPolicy(max_retries=2),
        structured_output=True,
        reasoning="standard",
    ),
    AICapability.MISSION_NARRATIVE: CapabilityProfile(
        temperature=0.4,
        max_tokens=2048,
        timeout_seconds=20,
        retry_policy=RetryPolicy(max_retries=1),
        structured_output=True,
        reasoning="fast",
        latency_priority="low",
        cost_priority="economy",
    ),
    AICapability.ASSESSMENT_CONTENT: CapabilityProfile(
        temperature=0.5,
        max_tokens=4096,
        timeout_seconds=45,
        retry_policy=RetryPolicy(max_retries=2),
        structured_output=True,
        reasoning="deep",
        latency_priority="relaxed",
        cost_priority="premium",
    ),
}


class CapabilityRegistry:
    """Registry of capability → profile mappings.

    Consumer code must go through this registry to obtain execution
    parameters.  Direct dictionary access to capability profiles is
    forbidden outside this class.
    """

    def __init__(self) -> None:
        self._profiles: Dict[AICapability, CapabilityProfile] = dict(_DEFAULT_PROFILES)

    def register(self, capability: AICapability, profile: CapabilityProfile) -> None:
        """Register or override a capability profile."""
        self._profiles[capability] = profile
        logger.info("Capability registered: %s", capability.value)

    def resolve(self, capability: AICapability) -> CapabilityProfile:
        """Return the profile for *capability*, or raise ``AIProviderError``."""
        profile = self._profiles.get(capability)
        if profile is None:
            raise AIProviderError(
                f"Unknown AI capability: {capability.value}",
                kind="invalid_capability",
                status_code=400,
            )
        return profile

    def is_registered(self, capability: AICapability) -> bool:
        """Check whether a capability has a registered profile."""
        return capability in self._profiles


# ===========================================================================
# Provider Registry
# ===========================================================================

class ProviderRegistry:
    """Stores discovered providers.  Owns environment-variable discovery.

    ``load_from_environment()`` reads API key env vars, instantiates
    adapters, creates ``ProviderDefinition`` entries, and registers them.
    The registry is the single source of truth for which providers are
    available in this process.  Does NOT make routing decisions.
    """

    def __init__(self) -> None:
        self._providers: Dict[str, ProviderDefinition] = {}

    # ---- Environment discovery -----------------------------------------

    def load_from_environment(self) -> None:
        """Read environment variables and register all available providers.

        Provider adapters are stateless — they know nothing about env vars,
        priorities, or configuration.  This method owns all of that.

        Adding a new provider requires:
            1. A new adapter in ``ai_gateway/providers/``.
            2. An env-var check in this method.
            3. Setting the env var in deployment.

        Zero changes to ``gateway.py``, ``routing.py`` routing policy,
        or any consumer module.
        """
        all_capabilities = set(AICapability)

        # -- Gemini (primary) -----------------------------------------------
        gemini_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
        gemini_model = (os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash").strip()
        if gemini_key:
            from ai_gateway.providers.gemini import GeminiAdapter

            self.register(ProviderDefinition(
                id="gemini-primary",
                priority=10,
                capabilities=set(all_capabilities),
                model=gemini_model,
                api_key=gemini_key,
                transport="direct",
                adapter=GeminiAdapter(),
            ))
            logger.info("Provider registered: gemini-primary (model=%s)", gemini_model)

        # -- Gemini (emergent fallback) -------------------------------------
        emergent_key = (os.environ.get("EMERGENT_LLM_KEY") or "").strip()
        emergent_model = (os.environ.get("EMERGENT_LLM_MODEL") or "gemini-2.5-flash").strip()
        if emergent_key and emergent_key != gemini_key:
            from ai_gateway.providers.gemini import GeminiAdapter

            self.register(ProviderDefinition(
                id="gemini-emergent",
                priority=20,
                capabilities=set(all_capabilities),
                model=emergent_model,
                api_key=emergent_key,
                transport="direct",
                adapter=GeminiAdapter(),
            ))
            logger.info("Provider registered: gemini-emergent (model=%s)", emergent_model)

        # -- OpenRouter (preferred) -------------------------------------------
        openrouter_key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
        openrouter_model = (
            os.environ.get("OPENROUTER_DEFAULT_MODEL") or "google/gemini-2.5-flash"
        ).strip()
        if openrouter_key:
            from ai_gateway.providers.openrouter import OpenRouterAdapter

            self.register(ProviderDefinition(
                id="openrouter",
                priority=5,
                capabilities=set(all_capabilities),
                model=openrouter_model,
                api_key=openrouter_key,
                transport="direct",
                adapter=OpenRouterAdapter(),
            ))
            logger.info("Provider registered: openrouter (default_model=%s)", openrouter_model)

        if not self._providers:
            logger.warning(
                "No AI providers discovered.  Set GEMINI_API_KEY or "
                "EMERGENT_LLM_KEY to enable AI features."
            )

    # ---- Registry operations -------------------------------------------

    def register(self, definition: ProviderDefinition) -> None:
        """Add a provider to the registry."""
        self._providers[definition.id] = definition

    def get_all(self) -> List[ProviderDefinition]:
        """Return all registered providers (unordered)."""
        return list(self._providers.values())

    def get_by_id(self, provider_id: str) -> Optional[ProviderDefinition]:
        """Lookup a single provider by ID, or ``None``."""
        return self._providers.get(provider_id)

    @property
    def count(self) -> int:
        """Number of registered providers."""
        return len(self._providers)


# ===========================================================================
# Routing Policy
# ===========================================================================

class RoutingPolicy:
    """Decides which providers to try and in what order.

    The routing policy owns:
        - provider priority ordering
        - capability-based filtering
        - future: latency-based, cost-based, round-robin routing

    It is deliberately separated from the ``ProviderRegistry`` so that
    routing logic can evolve without touching provider discovery.
    """

    def resolve_chain(
        self,
        capability: AICapability,
        registry: ProviderRegistry,
    ) -> List[ProviderDefinition]:
        """Return an ordered list of providers that support *capability*.

        Providers are filtered by capability support and sorted by
        priority (lower = preferred).  Returns an empty list if no
        providers support the requested capability.
        """
        candidates = [
            p for p in registry.get_all()
            if capability in p.capabilities and p.adapter is not None
        ]
        candidates.sort(key=lambda p: p.priority)
        return candidates
