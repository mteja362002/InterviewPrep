"""Public AI service façade.

This module is the **only** public entry point for AI completions in the
PrepOS codebase.  All consumer modules (knowledge generation, AI mentor,
mission planner) import from here — never from ``ai_gateway`` directly.

Responsibilities (exhaustive list):
    1. Validate inputs (non-empty prompt, valid capability).
    2. Construct ``AIRequest``.
    3. Obtain the gateway via ``get_gateway()``.
    4. Call ``gateway.complete(request)``.
    5. Return the generated text as ``str``.
    6. Re-export ``AICapability`` and ``AIProviderError``.

NOT responsible for:
    - Routing
    - Retry logic
    - Provider selection
    - SDK imports (``google.genai``, ``litellm``, etc.)
    - Error classification
    - Health monitoring
    - Telemetry
"""
from __future__ import annotations

import logging

from ai_gateway import (
    AICapability,
    AIProviderError,
    AIRequest,
    get_gateway,
)

logger = logging.getLogger(__name__)

# Re-export gateway types so existing imports continue to work:
#   from ai_service import AIProviderError
#   from ai_service import AICapability
__all__ = ["AICapability", "AIProviderError", "complete"]


async def complete(
    *,
    capability: AICapability,
    system_message: str,
    prompt: str,
    session_id: str = "",
) -> str:
    """Execute an AI completion through the gateway.

    Returns the raw generated text.  ``AIResponse`` metadata (provider,
    model, latency) is kept internal to the gateway for telemetry;
    consumers receive only the text they need.

    Raises ``AIProviderError`` if all providers fail.
    """
    if not prompt or not prompt.strip():
        raise AIProviderError(
            "AI prompt must not be empty.",
            kind="invalid_request",
            status_code=400,
        )

    request = AIRequest(
        capability=capability,
        system_message=system_message,
        prompt=prompt,
        session_id=session_id,
    )

    gateway = get_gateway()
    response = await gateway.complete(request)
    return response.text