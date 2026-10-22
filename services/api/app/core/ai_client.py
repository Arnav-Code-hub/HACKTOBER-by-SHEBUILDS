"""Typed HTTP client for services/ai.

The API is the ONLY caller of the AI service — it is never exposed publicly and
never touches the business database. Every AI result crosses back through here
and is validated before anything persists it.

Fast, user-blocking work goes through these methods. Slow or expensive work
(OCR, speech-to-text, embedding backfill, before/after image analysis) is
enqueued onto the worker instead — see app/modules/*/tasks.py.
"""

from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import UpstreamError


class AIClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = httpx.AsyncClient(
            base_url=settings.ai_service_url,
            timeout=settings.ai_request_timeout_seconds,
            headers={"X-Internal-Key": settings.ai_service_key},
        )

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._client.post(path, json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise UpstreamError(f"AI service call to {path} failed: {exc}") from exc
        return response.json()  # type: ignore[no-any-return]

    async def classify(self, text: str, language: str | None = None) -> dict[str, Any]:
        """Free-text report → category, severity, suggested department."""
        return await self._post("/v1/classify", {"text": text, "language": language})

    async def embed(self, texts: list[str]) -> dict[str, Any]:
        """Embeddings for duplicate detection. Vectors are stored by the API."""
        return await self._post("/v1/embed", {"texts": texts})

    async def translate(self, text: str, target: str) -> dict[str, Any]:
        return await self._post("/v1/translate", {"text": text, "target": target})

    async def close(self) -> None:
        await self._client.aclose()
