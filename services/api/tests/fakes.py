"""Explicit fake provider boundaries; never imported into application code."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeCloudinary:
    assets: dict[str, dict[str, Any]] = field(default_factory=dict)
    deleted: list[str] = field(default_factory=list)

    async def resource(self, public_id: str) -> dict[str, Any]:
        return dict(self.assets[public_id])

    async def destroy(self, public_id: str) -> None:
        self.assets.pop(public_id, None)
        self.deleted.append(public_id)


@dataclass
class FakeGemini:
    response: dict[str, Any] = field(default_factory=dict)
    failure: Exception | None = None
    calls: list[str] = field(default_factory=list)

    async def suggest(self, transcript: str) -> dict[str, Any]:
        self.calls.append(transcript)
        if self.failure is not None:
            raise self.failure
        return dict(self.response)
