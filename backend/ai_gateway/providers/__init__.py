"""Provider auto-discovery and adapter registry.

On import, reads environment variables and instantiates the adapters
for every configured provider.  The ``discover()`` function returns a
list of ``ProviderDefinition`` entries ready for the ``ProviderRegistry``.

Adding a new provider requires:
    1. A new adapter module in ``ai_gateway/providers/``.
    2. An env-var check in ``discover()`` below.
    3. Setting the env var in deployment.

Zero changes to ``gateway.py``, ``routing.py``, or any consumer module.
"""
from __future__ import annotations

import logging
import os
from typing import List

from ai_gateway.models import AICapability, ProviderDefinition

log = logging.getLogger(__name__)

# Every registered capability that the Gemini adapter supports.
_ALL_CAPABILITIES = set(AICapability)


def discover() -> List[ProviderDefinition]:
    """Read environment variables and build provider definitions.

    Providers are instantiated lazily — only when their API key env var
    is set and non-empty.  Returns an ordered list (by priority).
    """
    providers: List[ProviderDefinition] = []

    # -- Gemini (primary) ---------------------------------------------------
    gemini_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    gemini_model = (os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash").strip()
    if gemini_key:
        from ai_gateway.providers.gemini import GeminiAdapter

        providers.append(ProviderDefinition(
            id="gemini-primary",
            priority=10,
            capabilities=set(_ALL_CAPABILITIES),
            model=gemini_model,
            api_key=gemini_key,
            transport="direct",
            adapter=GeminiAdapter(),
        ))
        log.info("Provider registered: gemini-primary (model=%s)", gemini_model)

    # -- Gemini (emergent fallback) -----------------------------------------
    emergent_key = (os.environ.get("EMERGENT_LLM_KEY") or "").strip()
    emergent_model = (os.environ.get("EMERGENT_LLM_MODEL") or "gemini-2.5-flash").strip()
    if emergent_key and emergent_key != gemini_key:
        from ai_gateway.providers.gemini import GeminiAdapter

        providers.append(ProviderDefinition(
            id="gemini-emergent",
            priority=20,
            capabilities=set(_ALL_CAPABILITIES),
            model=emergent_model,
            api_key=emergent_key,
            transport="direct",
            adapter=GeminiAdapter(),
        ))
        log.info("Provider registered: gemini-emergent (model=%s)", emergent_model)

    # -- OpenRouter (future) ------------------------------------------------
    openrouter_key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if openrouter_key:
        log.info("OpenRouter key detected — adapter not yet implemented, skipping")

    if not providers:
        log.warning(
            "No AI providers discovered.  Set GEMINI_API_KEY or "
            "EMERGENT_LLM_KEY to enable AI features."
        )

    return providers
