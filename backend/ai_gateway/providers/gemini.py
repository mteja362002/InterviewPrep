"""Gemini provider adapter.

Encapsulates all ``google.genai`` SDK usage.  No other module in the
codebase should import ``google.genai`` directly — this adapter is the
sole owner of the Gemini transport.

The SDK import is deferred to the first ``complete()`` call so the
package can be imported in environments where ``google-genai`` is not
installed (e.g. test runners).

Migrated from ``ai_service._call_llm``.
"""
from __future__ import annotations

import logging

from .base import ProviderAdapter

log = logging.getLogger(__name__)


class GeminiAdapter(ProviderAdapter):
    """Adapter for the Google Gemini API via the ``google-genai`` SDK."""

    @property
    def name(self) -> str:
        return "gemini"

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
        """Call Gemini via ``google.genai`` and return the raw text response.

        The SDK import is deferred to here so the adapter module can be
        imported without ``google-genai`` being installed.

        Raises a raw exception on failure — the caller (gateway execution
        loop) is responsible for classifying it via ``classify_error()``.
        """
        from google import genai

        client = genai.Client(api_key=api_key)

        interaction = client.interactions.create(
            model=model,
            input=prompt,
            system_instruction=system_message if system_message else None,
        )

        response = interaction.output_text

        if not response:
            raise RuntimeError("AI returned an empty response")

        return str(response) if not isinstance(response, str) else response
