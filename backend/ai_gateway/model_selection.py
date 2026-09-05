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
from dataclasses import dataclass
from typing import Dict, Mapping, Tuple

from ai_gateway.models import AICapability, CapabilityProfile, ProviderDefinition

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OpenRouter model tiers — edit HERE when swapping models.
#
# Each tier maps a ``reasoning`` level from CapabilityProfile to an ordered
# list of eligible OpenRouter models. Candidate capabilities are declared in
# this gateway-internal registry and deterministically matched to a profile.
# The configured order is only the final tie-breaker; it is not a hard-coded
# provider-family decision.
#
# ``OPENROUTER_MODEL_<TIER>`` accepts either one model ID (the existing
# contract) or a comma-separated ordered candidate list.
#
# Defaults verified against OpenRouter model pages on 2026-09-05:
#
#   fast     → Google Gemini 3.5 Flash-Lite, OpenAI GPT-4.1 Mini,
#              Qwen3 30B A3B Instruct 2507.
#
#   standard → Google Gemini 2.5 Flash, OpenAI GPT-4.1 Mini,
#              Qwen3 30B A3B Instruct 2507.
#
#   deep     → Google Gemini 2.5 Pro, Anthropic Claude Sonnet 4.5,
#              DeepSeek R1 0528.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelCandidate:
    """Static capability declaration for one OpenRouter model.

    This is intentionally configuration, not a live model catalogue.  It
    makes the policy inspectable and lets future gateway-owned task context
    add deterministic constraints without exposing models to consumers.
    """

    model_id: str
    family: str
    reasoning_strength: str  # "fast" | "standard" | "deep"
    latency_class: str       # "low" | "balanced" | "relaxed"
    cost_class: str          # "economy" | "balanced" | "premium"
    supports_structured_output: bool


_MODEL_CAPABILITY_REGISTRY: Dict[str, ModelCandidate] = {
    "google/gemini-3.5-flash-lite": ModelCandidate(
        "google/gemini-3.5-flash-lite", "google", "fast", "low", "economy", True,
    ),
    "openai/gpt-4.1-mini": ModelCandidate(
        "openai/gpt-4.1-mini", "openai", "standard", "low", "balanced", True,
    ),
    "qwen/qwen3-30b-a3b-instruct-2507": ModelCandidate(
        "qwen/qwen3-30b-a3b-instruct-2507", "qwen", "standard", "low", "economy", True,
    ),
    "google/gemini-2.5-flash": ModelCandidate(
        "google/gemini-2.5-flash", "google", "standard", "balanced", "balanced", True,
    ),
    "google/gemini-2.5-pro": ModelCandidate(
        "google/gemini-2.5-pro", "google", "deep", "relaxed", "premium", True,
    ),
    "anthropic/claude-sonnet-4.5": ModelCandidate(
        "anthropic/claude-sonnet-4.5", "anthropic", "deep", "relaxed", "premium", True,
    ),
    "deepseek/deepseek-r1-0528": ModelCandidate(
        "deepseek/deepseek-r1-0528", "deepseek", "deep", "relaxed", "balanced", True,
    ),
}

_REASONING_RANK = {"fast": 0, "standard": 1, "deep": 2}

_DEFAULT_TIER_CANDIDATES: Dict[str, str] = {
    "fast": (
        "google/gemini-3.5-flash-lite,openai/gpt-4.1-mini,"
        "qwen/qwen3-30b-a3b-instruct-2507"
    ),
    "standard": (
        "google/gemini-2.5-flash,openai/gpt-4.1-mini,"
        "qwen/qwen3-30b-a3b-instruct-2507"
    ),
    "deep": (
        "google/gemini-2.5-pro,anthropic/claude-sonnet-4.5,"
        "deepseek/deepseek-r1-0528"
    ),
}

def _configured_candidates(env_name: str, default: str) -> Tuple[str, ...]:
    """Return a de-duplicated, ordered model list from one env setting."""
    configured = os.environ.get(env_name, default)
    candidates = tuple(dict.fromkeys(
        model.strip() for model in configured.split(",") if model.strip()
    ))
    return candidates or (default,)


_MODEL_CANDIDATES: Dict[str, Tuple[str, ...]] = {
    tier: _configured_candidates(f"OPENROUTER_MODEL_{tier.upper()}", default)
    for tier, default in _DEFAULT_TIER_CANDIDATES.items()
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

    def __init__(
        self,
        model_registry: Mapping[str, ModelCandidate] | None = None,
    ) -> None:
        self._model_registry = (
            model_registry if model_registry is not None else _MODEL_CAPABILITY_REGISTRY
        )

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
            candidates = self._select_for_openrouter_candidates(profile)
            # ``select`` remains a simple compatibility API. Gateway uses
            # ``select_candidates`` and can therefore fail over if no model
            # satisfies a hard requirement.
            model = candidates[0] if candidates else provider.model
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

    def _select_for_openrouter(self, profile: CapabilityProfile) -> str:
        """Map capability requirements to an OpenRouter model.

        The selection algorithm filters out candidates that cannot satisfy
        structured-output or minimum reasoning requirements. It then sorts
        eligible candidates by: exact latency class, exact cost class, least
        excess reasoning strength, then configured order.
        """
        return self._select_for_openrouter_candidates(profile)[0]

    def _select_for_openrouter_candidates(self, profile: CapabilityProfile) -> Tuple[str, ...]:
        """Return eligible candidates, deterministically ordered for execution."""
        reasoning = getattr(profile, "reasoning", "standard")
        requested_rank = _REASONING_RANK.get(reasoning, _REASONING_RANK["standard"])
        configured = _MODEL_CANDIDATES.get(reasoning, _MODEL_CANDIDATES["standard"])
        candidates = tuple(
            self._model_registry.get(model_id) or ModelCandidate(
                model_id=model_id,
                family="custom",
                reasoning_strength=reasoning,
                latency_class="balanced",
                cost_class="balanced",
                supports_structured_output=True,
            )
            for model_id in configured
        )
        eligible = [
            candidate for candidate in candidates
            if _REASONING_RANK.get(candidate.reasoning_strength, 0) >= requested_rank
            and (not profile.structured_output or candidate.supports_structured_output)
        ]

        ranked = sorted(
            enumerate(eligible),
            key=lambda item: self._candidate_sort_key(
                item[1], item[0], profile, requested_rank,
            ),
        )
        return tuple(candidate.model_id for _, candidate in ranked)

    @staticmethod
    def _candidate_sort_key(
        candidate: ModelCandidate,
        configured_index: int,
        profile: CapabilityProfile,
        requested_rank: int,
    ) -> tuple[bool, bool, int, int]:
        """A transparent lexicographic policy; no opaque weighted score."""
        return (
            candidate.latency_class != profile.latency_priority,
            candidate.cost_class != profile.cost_priority,
            _REASONING_RANK.get(candidate.reasoning_strength, requested_rank) - requested_rank,
            configured_index,
        )
