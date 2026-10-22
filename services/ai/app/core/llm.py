"""Provider-agnostic LLM interface.

Every capability calls this, never a vendor SDK directly. Swapping Gemini for a
self-hosted model at a government deployment then touches one file instead of
ten capabilities.
"""

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Implemented per vendor. Selected by LLM_PROVIDER."""

    @abstractmethod
    async def complete(
        self, prompt: str, *, schema: dict[str, Any] | None = None, **kwargs: Any
    ) -> str:
        """Generate a completion. Pass `schema` to force structured output."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts for similarity search."""


def get_provider() -> LLMProvider:
    """Resolve the configured provider.

    TODO(llm): GeminiProvider, OpenAIProvider, LocalProvider.
    """
    raise NotImplementedError("Implement providers in app/core/providers/")
