"""AI Gateway — public package exports.

Usage from consumer code (via ``ai_service.py`` façade only)::

    from ai_service import AICapability, AIProviderError

Direct imports from ``ai_gateway`` are reserved for ``ai_service.py``.
Consumer modules must never import from this package directly.

The gateway instance is created lazily on first access via
``get_gateway()`` — no import-time side effects.
"""
from __future__ import annotations

from typing import Optional

from ai_gateway.gateway import Gateway
from ai_gateway.models import (
    AICapability,
    AIProviderError,
    AIRequest,
    AIResponse,
)

# Lazy singleton — created on first get_gateway() call.
_gateway: Optional[Gateway] = None


def get_gateway() -> Gateway:
    """Return the singleton ``Gateway`` instance, creating it on first call.

    Advantages of lazy initialisation:
        - zero import-time side effects
        - easier testing (mock or replace before first call)
        - future: dependency injection, configuration reloads
    """
    global _gateway
    if _gateway is None:
        _gateway = Gateway()
    return _gateway


__all__ = [
    "Gateway",
    "AICapability",
    "AIProviderError",
    "AIRequest",
    "AIResponse",
    "get_gateway",
]
