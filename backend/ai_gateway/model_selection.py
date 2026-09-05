"""Centralised model selection for the AI Gateway.

The ``ModelSelector`` converts capability requirements (reasoning level,
latency preference, cost preference) into a provider-specific model ID.

Consumer modules NEVER see model names.  Model selection is a private,
gateway-internal concern.

Architecture::

    Consumer → ai_service.complete(capability)
                    ↓
    Gateway  → CapabilityProfile (requirements)
                    ↓
             → ModelSelector.select(profile, provider)
                    ↓  (for OpenRouter)
             → configured candidate list for profile.reasoning
                    ↓
             → preferred configured model ID

Adding or changing models requires editing ONLY this file.
Zero consumer changes.  Zero routing changes.  Zero adapter changes.
"""
from __future__ import annotations

import logging
import os
from typing import Dict, Tuple

from ai_gateway.models import AICapability, CapabilityProfile, ProviderDefinition

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OpenRouter model tiers — edit HERE when swapping models.
#
# Each tier maps a ``reasoning`` level from CapabilityProfile to an ordered
# list of eligible OpenRouter models.  The first entry is the normal choice;
# later entries are deterministic fallbacks when OpenRouter reports that a
# configured model is unavailable.  This keeps model-family choice inside the
# gateway while allowing an operator to configure non-Gemini OpenRouter models
# without consumer or routing changes.
#
# ``OPENROUTER_MODEL_<TIER>`` accepts either one model ID (the existing
# contract) or a comma-separated ordered candidate list.
#
# Defaults verified against OpenRouter /api/v1/models on 2026-09-05:
#
#   fast     → google/gemini-3.5-flash-lite
#              Newest lightweight model.  Low latency, low cost.
#              Ideal for narrative generation, simple formatting.
#
#   standard → google/gemini-2.5-flash
#              Proven workhorse.  Good structured output, balanced cost.
#              Ideal for knowledge generation, lessons, mentor chat.
#
#   deep     → google/gemini-2.5-pro
#              Strongest reasoning.  Higher latency/cost, best quality.
#              Ideal for complex explanations, difficult assessments.
# ---------------------------------------------------------------------------

def _configured_candidates(env_name: str, default: str) -> Tuple[str, ...]:
    """Return a de-duplicated, ordered model list from one env setting."""
    configured = os.environ.get(env_name, default)
    candidates = tuple(dict.fromkeys(
        model.strip() for model in configured.split(",") if model.strip()
    ))
    return candidates or (default,)


_MODEL_CANDIDATES: Dict[str, Tuple[str, ...]] = {
    "fast": _configured_candidates(
        "OPENROUTER_MODEL_FAST", "google/gemini-3.5-flash-lite",
    ),
    "standard": _configured_candidates(
        "OPENROUTER_MODEL_STANDARD", "google/gemini-2.5-flash",
    ),
    "deep": _configured_candidates(
        "OPENROUTER_MODEL_DEEP", "google/gemini-2.5-pro",
    ),
}

# Kept as the current tier's primary model for backwards-compatible imports
# and simple configuration inspection.  Selection uses _MODEL_CANDIDATES.
_MODEL_TIERS: Dict[str, str] = {
    tier: candidates[0] for tier, candidates in _MODEL_CANDIDATES.items()
}


class ModelSelector:
    """Selects the optimal model for a (capability, provider) combination.

    Design principles:
        * Capabilities describe **requirements** (reasoning, latency, cost).
        * The selector converts requirements into a **concrete model ID**.
        * Provider-specific logic is encapsulated here — not in adapters,
          not in routing, not in consumers.
        * The selector is stateless and safe to share across requests.

    For OpenRouter:
        Maps ``CapabilityProfile.reasoning`` to the model tier table above.

    For Gemini direct (and any other provider):
        Returns the provider's configured ``model`` field unchanged.
    """

    def select(
        self,
        *,
        capability: AICapability,
        profile: CapabilityProfile,
        provider: ProviderDefinition,
    ) -> str:
        """Return the model ID to use for this capability + provider.

        Parameters
        ----------
        capability : AICapability
            The requested capability (used for logging only).
        profile : CapabilityProfile
            The resolved capability requirements.
        provider : ProviderDefinition
            The provider about to be called.

        Returns
        -------
        str
            A model identifier suitable for the provider's API.
        """
        adapter_name = getattr(provider.adapter, "name", None) if provider.adapter else None
        if adapter_name == "openrouter":
            model = self._select_for_openrouter(profile)
            logger.debug(
                "ModelSelector: %s → %s (reasoning=%s, provider=%s)",
                capability.value, model,
                getattr(profile, "reasoning", "standard"),
                provider.id,
            )
            return model

        # Non-OpenRouter providers: use the provider's configured model.
        return provider.model

    def select_candidates(
        self,
        *,
        capability: AICapability,
        profile: CapabilityProfile,
        provider: ProviderDefinition,
    ) -> Tuple[str, ...]:
        """Return deterministic eligible models in preference order.

        The gateway normally uses the first model.  It can try a later
        OpenRouter candidate only if the previous one is unavailable; this is
        intentionally not a runtime catalogue lookup or scoring system.
        """
        adapter_name = getattr(provider.adapter, "name", None) if provider.adapter else None
        if adapter_name == "openrouter":
            return self._select_for_openrouter_candidates(profile)
        return (provider.model,)

    # ------------------------------------------------------------------
    # Provider-specific selection logic
    # ------------------------------------------------------------------

    @staticmethod
    def _select_for_openrouter(profile: CapabilityProfile) -> str:
        """Map capability requirements to an OpenRouter model.

        The selection algorithm:
            1. Read ``profile.reasoning`` — the primary signal.
            2. Look up the model tier table.
            3. Fall back to the global default.

        Future: incorporate ``latency_priority``, ``cost_priority``, and
        ``structured_output`` for finer-grained selection when the model
        catalogue grows.
        """
        return ModelSelector._select_for_openrouter_candidates(profile)[0]

    @staticmethod
    def _select_for_openrouter_candidates(profile: CapabilityProfile) -> Tuple[str, ...]:
        """Return configured candidates for the requested reasoning tier."""
        reasoning = getattr(profile, "reasoning", "standard")
        return _MODEL_CANDIDATES.get(reasoning, _MODEL_CANDIDATES["standard"])
