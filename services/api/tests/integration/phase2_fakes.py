"""Test-only provider boundary; no fake identity is reachable in runtime code."""

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException

from app.core.errors import UpstreamError
from app.core.evidence import EvidenceCard


class TokenVerifier:
    async def verify(self, token: str) -> str:
        if not token.startswith("valid:"):
            raise HTTPException(401, "Invalid or expired authentication token.")
        return token.removeprefix("valid:")


class MediaProvider:
    def __init__(self) -> None:
        self.assets: dict[str, dict[str, Any]] = {}
        self.fail = False
        self.calls = 0
        self.cards: list[EvidenceCard] = []

    def authorize(self, public_id: str, timestamp: int) -> tuple[str, dict[str, str]]:
        return "https://api.cloudinary.com/v1_1/test/image/upload", {
            "public_id": public_id,
            "timestamp": str(timestamp),
            "overwrite": "false",
            "allowed_formats": "jpg,jpeg,png,webp",
            "api_key": "public-test-key",
            "signature": "a" * 64,
        }

    def verify_response(self, public_id: str, version: int, signature: str) -> bool:
        return signature == "a" * 40

    async def resource(self, public_id: str) -> dict[str, Any]:
        self.calls += 1
        if self.fail or public_id not in self.assets:
            raise UpstreamError("Photo verification unavailable; retry shortly.")
        return self.assets[public_id]

    def delivery(self, public_id: str, version: int, *, thumbnail: bool) -> str:
        variant = "thumb" if thumbnail else "detail"
        return f"https://res.cloudinary.com/test/image/upload/{variant}/v{version}/{public_id}"

    def panel(self, public_id: str, version: int) -> str:
        return f"https://res.cloudinary.com/test/image/upload/panel/v{version}/{public_id}"

    def evidence_card(self, card: EvidenceCard) -> str:
        import hashlib

        self.cards.append(card)
        key = hashlib.sha256(repr(card).encode()).hexdigest()
        return f"https://res.cloudinary.com/test/image/upload/card/{key}"

    def uploaded(self, expected_id: str, **overrides: Any) -> None:
        self.assets[expected_id] = {
            "public_id": expected_id,
            "asset_id": f"test:{expected_id}",
            "version": 123,
            "resource_type": "image",
            "type": "upload",
            "format": "jpg",
            "bytes": 12345,
            "width": 640,
            "height": 480,
            "created_at": datetime.now(UTC).isoformat(),
            **overrides,
        }
