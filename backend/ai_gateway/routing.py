"""Capability registry, provider registry, and routing policy.

Three distinct responsibilities in one cohesive module:

``CapabilityRegistry``
    Owns capability → profile mapping.  Validates capability names and
    returns ``CapabilityProfile`` instances.  Consumer code must never
    access capability profiles directly.

``ProviderRegistry``
    Knows **which** providers are available.  Stores ``ProviderDefinition``
    entries discovered at startup.  Does NOT make routing decisions.

``RoutingPolicy``
    Decides **which** provider to try and in **what order**.  Consults
    the provider registry, filters by capability support, and orders by
    priority.  Owns all future routing strategies (latency-based,
    cost-based, round-robin).
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from ai_gateway.models import (
    AICapability,
    AIProviderError,
    CapabilityProfile,
    ProviderDefinition,
    RetryPolicy,
)

log = logging.getLogger(__name__)


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
    ),
    AICapability.MENTOR_CHAT: CapabilityProfile(
        temperature=0.6,
        max_tokens=4096,
        timeout_seconds=30,
        retry_policy=RetryPolicy(max_retries=2),
    ),
    AICapability.MENTOR_LESSON: CapabilityProfile(
        temperature=0.6,
        max_tokens=4096,
        timeout_seconds=30,
        retry_policy=RetryPolicy(max_retries=2),
        structured_output=True,
    ),
    AICapability.MISSION_NARRATIVE: CapabilityProfile(
        temperature=0.4,
        max_tokens=2048,
        timeout_seconds=20,
        retry_policy=RetryPolicy(max_retries=1),
        structured_output=True,
    ),
    AICapability.ASSESSMENT_CONTENT: CapabilityProfile(
        temperature=0.5,
        max_tokens=4096,
        timeout_seconds=30,
        retry_policy=RetryPolicy(max_retries=2),
        structured_output=True,
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
        log.info("Capability registered: %s", capability.value)

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
    """Stores discovered providers.  No routing logic.

    Populated once at startup via ``discover()`` from
    ``ai_gateway.providers``.  The registry is the single source of truth
    for which providers are available in this process.
    """

    def __init__(self) -> None:
        self._providers: Dict[str, ProviderDefinition] = {}

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
