"""AI Gateway domain models.

Defines the typed contracts used across the gateway:
    - AICapability   — enum of registered AI capabilities
    - CapabilityProfile — execution parameters per capability
    - RetryPolicy    — retry configuration
    - AIRequest      — typed request flowing into the gateway
    - AIResponse     — typed response (internal to gateway + telemetry)
    - AIProviderError — structured exception for AI failures
    - ProviderDefinition — provider metadata separated from adapter logic

All consumer-facing types are re-exported via ``ai_service.py``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, Optional, Set


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------

class AICapability(str, Enum):
    """Registered AI capabilities.  Consumers reference these — never raw strings."""
    KNOWLEDGE_GENERATION = "knowledge_generation"
    MENTOR_CHAT          = "mentor_chat"
    MENTOR_LESSON        = "mentor_lesson"
    MISSION_NARRATIVE    = "mission_narrative"
    ASSESSMENT_CONTENT   = "assessment_content"


# ---------------------------------------------------------------------------
# Retry / Execution policies
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RetryPolicy:
    """Retry configuration for a capability or provider.

    ``retryable_kinds`` lists the AIProviderError *kind* strings that warrant
    a retry.  Non-retryable errors (e.g. ``invalid_key``) skip immediately.
    """
    max_retries: int = 2
    base_delay_seconds: float = 1.0
    backoff: str = "exponential"                     # "exponential" | "fixed"
    retryable_kinds: FrozenSet[str] = frozenset({
        "timeout", "rate_limit", "upstream",
    })


# ---------------------------------------------------------------------------
# Capability profiles
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CapabilityProfile:
    """Execution parameters for a single capability.

    Centralised here so that temperatures, token budgets, and timeout values
    are *never* scattered across consumer modules.

    Model selection requirements (``reasoning``, ``latency_priority``,
    ``cost_priority``) are used by ``ModelSelector`` to pick the optimal
    model for a given provider.  Consumers never see these fields.
    """
    temperature: float
    max_tokens: int
    timeout_seconds: int
    retry_policy: RetryPolicy
    structured_output: bool = False
    streaming: bool = False
    # -- Model selection requirements (used by ModelSelector) ---------------
    reasoning: str = "standard"           # "fast" | "standard" | "deep"
    latency_priority: str = "balanced"    # "low" | "balanced" | "relaxed"
    cost_priority: str = "balanced"       # "economy" | "balanced" | "premium"


# ---------------------------------------------------------------------------
# Request / Response
# ---------------------------------------------------------------------------

@dataclass
class AIRequest:
    """Typed request flowing through the gateway.

    Consumers supply ``capability``, ``system_message``, and ``prompt``.
    The gateway resolves execution parameters (temperature, tokens, timeout)
    internally from the corresponding ``CapabilityProfile``.
    """
    capability: AICapability
    system_message: str
    prompt: str
    session_id: str = ""


@dataclass
class AIResponse:
    """Typed response from the gateway.

    **Internal to the gateway.**  ``ai_service.complete()`` extracts
    ``response.text`` and returns plain ``str`` to consumers.  The full
    ``AIResponse`` is available for telemetry and future metadata needs.
    """
    text: str
    provider_used: str
    model_used: str
    latency_ms: int
    capability: AICapability


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class AIProviderError(Exception):
    """Structured error raised when an AI provider call fails.

    Re-exported via ``ai_service.py`` so existing import paths
    (``from ai_service import AIProviderError``) continue to work.
    """

    def __init__(
        self,
        message: str,
        *,
        kind: str = "unknown",
        status_code: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------

_INVALID_KEY_PATTERNS = (
    re.compile(r"api[\s_-]*key[^a-z]*(not[\s_]*valid|invalid|missing|rejected)", re.I),
    re.compile(r"api_key_invalid", re.I),
    re.compile(r"authenticationerror", re.I),
    re.compile(r"\bunauthorized\b", re.I),
    re.compile(r"\bpermission[\s_]*denied\b", re.I),
    re.compile(r"\b(401|403)\b"),
)
_RATE_LIMIT_PATTERNS = (
    re.compile(r"rate[\s_]*limit", re.I),
    re.compile(r"\bratelimiterror\b", re.I),
    re.compile(r"quota[\s_]*(exceeded|exhausted)", re.I),
    re.compile(r"\bresource[_\s]*exhausted\b", re.I),
    re.compile(r"\btoo[\s_]*many[\s_]*requests\b", re.I),
    re.compile(r"\b429\b"),
)
_MODEL_MISSING_PATTERNS = (
    re.compile(r"\bnotfounderror\b", re.I),
    re.compile(r"\binvalid[\s_]*model[\s_]*name\b", re.I),
    re.compile(r"model[^a-z]*(not[\s_]*found|does not exist|not available|not supported)", re.I),
    re.compile(r"unknown model", re.I),
    re.compile(r"\b404\b"),
)
_TIMEOUT_PATTERNS = (
    re.compile(r"\btimeout\b", re.I),
    re.compile(r"read[\s_]*timed[\s_]*out", re.I),
)
_NETWORK_PATTERNS = (
    re.compile(r"\bconnection[\s_]*(refused|error|reset|aborted)\b", re.I),
    re.compile(r"name[\s_]*resolution[\s_]*failed", re.I),
    re.compile(r"temporarily[\s_]*unavailable", re.I),
    re.compile(r"\bservice[\s_]*unavailable\b", re.I),
    re.compile(r"\b(502|503|504)\b"),
)


def _match_any(patterns: tuple, text: str) -> bool:
    return any(p.search(text) for p in patterns)


def classify_error(err: Exception) -> AIProviderError:
    """Bucket a raw SDK exception into a user-actionable ``AIProviderError``.

    Error messages are provider-neutral — they never reference
    "Settings page" or a specific provider name.
    """
    cls_name = err.__class__.__name__ or ""
    msg = str(err) or cls_name

    # --- fast path: match by exception class name --------------------------
    if cls_name in ("AuthenticationError", "PermissionDeniedError"):
        return AIProviderError(
            "AI authentication failed. Please contact support.",
            kind="invalid_key", status_code=401,
        )
    if cls_name in ("NotFoundError",):
        return AIProviderError(
            "The requested AI model is not available.",
            kind="model_not_found", status_code=404,
        )
    if cls_name in ("RateLimitError",):
        return AIProviderError(
            "AI rate limit reached. Try again in a minute.",
            kind="rate_limit", status_code=429,
        )
    if cls_name in ("Timeout", "APITimeoutError"):
        return AIProviderError(
            "AI request timed out. Retry in a moment.",
            kind="timeout", status_code=504,
        )
    if cls_name in ("APIConnectionError", "ServiceUnavailableError"):
        return AIProviderError(
            "AI service is temporarily unreachable. Retry in a moment.",
            kind="upstream", status_code=502,
        )

    # --- slow path: regex against the full error string --------------------
    if _match_any(_INVALID_KEY_PATTERNS, msg):
        return AIProviderError(
            "AI authentication failed. Please contact support.",
            kind="invalid_key", status_code=401,
        )
    if _match_any(_MODEL_MISSING_PATTERNS, msg):
        return AIProviderError(
            "The requested AI model is not available.",
            kind="model_not_found", status_code=404,
        )
    if _match_any(_RATE_LIMIT_PATTERNS, msg):
        return AIProviderError(
            "AI rate limit reached. Try again in a minute.",
            kind="rate_limit", status_code=429,
        )
    if _match_any(_TIMEOUT_PATTERNS, msg):
        return AIProviderError(
            "AI request timed out. Retry in a moment.",
            kind="timeout", status_code=504,
        )
    if _match_any(_NETWORK_PATTERNS, msg):
        return AIProviderError(
            "AI service is temporarily unreachable. Retry in a moment.",
            kind="upstream", status_code=502,
        )

    # --- fallback ----------------------------------------------------------
    trimmed = msg.strip().split("\n", 1)[0][:180]
    return AIProviderError(
        f"AI generation failed: {trimmed or cls_name or 'unknown error'}",
        kind="unknown", status_code=502,
    )


# ---------------------------------------------------------------------------
# Provider definitions
# ---------------------------------------------------------------------------

@dataclass
class ProviderDefinition:
    """Provider metadata — separated from adapter implementation.

    ``adapter`` is set after construction by the provider registry when
    discovery instantiates the concrete adapter class.
    """
    id: str                                         # e.g. "gemini-primary"
    priority: int                                   # lower = preferred
    capabilities: Set[AICapability]                 # which capabilities supported
    model: str                                      # default model for this entry
    api_key: str                                    # provider key (from env)
    transport: str = "direct"                       # "direct" | "litellm"
    adapter: object = field(default=None, repr=False)  # set by registry
