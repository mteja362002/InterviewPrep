"""AI Gateway — public package exports.

Usage from consumer code (via ``ai_service.py`` façade only)::

    from ai_service import AICapability, AIProviderError

Direct imports from ``ai_gateway`` are reserved for ``ai_service.py``.
Consumer modules must never import from this package directly.
"""
from ai_gateway.gateway import Gateway
from ai_gateway.models import (
    AICapability,
    AIProviderError,
    AIRequest,
    AIResponse,
)

# Singleton gateway instance — initialised lazily on first ``complete()`` call.
_gateway = Gateway()

__all__ = [
    "Gateway",
    "AICapability",
    "AIProviderError",
    "AIRequest",
    "AIResponse",
    "_gateway",
]
