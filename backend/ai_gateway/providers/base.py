"""Abstract provider adapter interface.

Every LLM provider (Gemini, OpenAI, Claude, etc.) implements this ABC.
The gateway never calls a provider SDK directly — only through an adapter.

Adapters contain **only** provider-specific execution logic.
Provider metadata (id, priority, capabilities) lives in ``ProviderDefinition``.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class ProviderAdapter(ABC):
    """Base class for all provider adapters.

    Subclasses implement ``complete()`` with provider-specific SDK calls.
    The adapter is stateless with respect to routing — it receives fully
    resolved parameters and returns raw text.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name (e.g. ``'gemini'``, ``'openrouter'``)."""

    @abstractmethod
    async def complete(
        self,
        *,
        model: str,
        api_key: str,
        system_message: str,
        prompt: str,
        temperature: float,
        max_tokens: int,
        timeout_seconds: int,
    ) -> str:
        """Execute a single completion and return the raw text response.

        Must raise a plain ``Exception`` on failure — the gateway's error
        classifier (``models.classify_error``) converts it to
        ``AIProviderError``.
        """
