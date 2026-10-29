"""Optional Gemini boundary. No business records and no logging of text."""

import json
from functools import lru_cache
from importlib.resources import files
from typing import TYPE_CHECKING, Any, Protocol

from app.core.config import Settings, get_settings

if TYPE_CHECKING:
    from google.genai.client import AsyncClient


class SuggestionProvider(Protocol):
    async def suggest(self, transcript: str, schema: dict[str, Any]) -> str | None: ...


@lru_cache(maxsize=1)
def classification_prompt() -> str:
    return files("app.prompts").joinpath("classify_v1.txt").read_text(encoding="utf-8")


@lru_cache(maxsize=2)
def _client(api_key: str, timeout_seconds: int) -> "AsyncClient":
    """One client per configuration, so calls reuse connections and TLS sessions
    instead of paying a handshake inside the timeout on every request."""
    from google import genai
    from google.genai import types

    # No fallback model, automatic tool calls, retries or persistent chat.
    # Gemini refuses a request deadline under 10 s; the caller's own
    # asyncio timeout still bounds how long a citizen waits.
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=max(timeout_seconds, 10) * 1000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    ).aio


class GeminiSuggestionProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def suggest(self, transcript: str, schema: dict[str, Any]) -> str | None:
        from google.genai import types

        contents = (
            "BEGIN_UNTRUSTED_TRANSCRIPT\n"
            + json.dumps({"transcript": transcript}, ensure_ascii=False)
            + "\nEND_UNTRUSTED_TRANSCRIPT"
        )
        budget = self.settings.gemini_thinking_budget
        client = _client(
            self.settings.gemini_api_key.get_secret_value(), self.settings.gemini_timeout_seconds
        )
        response = await client.models.generate_content(
            model=self.settings.gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=classification_prompt(),
                response_mime_type="application/json",
                response_json_schema=schema,
                candidate_count=1,
                # Thinking tokens count against the output limit and the
                # timeout; classification needs little or none.
                thinking_config=types.ThinkingConfig(thinking_budget=budget),
                max_output_tokens=1024 + max(budget, 0),
            ),
        )
        # Safety blocks, truncation and incomplete output never become hints.
        if not response.candidates or len(response.candidates) != 1:
            return None
        if response.candidates[0].finish_reason != types.FinishReason.STOP:
            return None
        return response.text


def get_suggestion_provider() -> SuggestionProvider:
    # Lazy construction: an unconfigured request never creates a Gemini client.
    return GeminiSuggestionProvider(get_settings())
