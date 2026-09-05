"""OpenRouter provider adapter.

Encapsulates all ``openai``-SDK usage for the OpenRouter API.  No other
module in the codebase should call OpenRouter directly — this adapter is
the sole owner of the OpenRouter transport.

OpenRouter exposes an OpenAI-compatible ``/v1/chat/completions`` endpoint,
so we reuse the official ``openai`` Python SDK with ``base_url`` pointed
at ``https://openrouter.ai/api/v1``.

The SDK import is deferred to the first ``complete()`` call so the
package can be imported in environments where ``openai`` is not installed
(e.g. test runners using mock adapters).

Migrated from: stub in routing.py → full adapter.
"""
from __future__ import annotations

import logging

from .base import ProviderAdapter

log = logging.getLogger(__name__)


class OpenRouterAdapter(ProviderAdapter):
    """Adapter for the OpenRouter multi-model API via the ``openai`` SDK."""

    @property
    def name(self) -> str:
        return "openrouter"

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
        """Call OpenRouter via the OpenAI-compatible SDK.

        The SDK import is deferred to here so the adapter module can be
        imported without ``openai`` being installed.

        Raises a raw exception on failure — the caller (gateway execution
        loop) is responsible for classifying it via ``classify_error()``.
        """
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://prepos.io",
                "X-Title": "PrepOS",
            },
        )

        messages: list[dict[str, str]] = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=float(timeout_seconds),
        )

        text = response.choices[0].message.content

        if not text:
            raise RuntimeError("AI returned an empty response")

        # Log token usage when available (cost tracking foundation).
        if response.usage:
            log.debug(
                "OpenRouter usage: prompt=%d completion=%d total=%d model=%s",
                response.usage.prompt_tokens or 0,
                response.usage.completion_tokens or 0,
                response.usage.total_tokens or 0,
                model,
            )

        return str(text) if not isinstance(text, str) else text
