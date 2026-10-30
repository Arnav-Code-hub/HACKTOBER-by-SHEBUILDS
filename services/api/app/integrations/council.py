"""Authenticated bounded HTTP transport; no council evaluation code."""

from uuid import UUID

import httpx
from pydantic import ValidationError as SchemaError

from app.core.errors import UpstreamError
from app.modules.council.schemas import CouncilEvidence, RemoteAssessment

MAX_RESPONSE = 8_000_000


class CouncilClient:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self.http = http

    async def request(self, method: str, path: str, **kwargs: object) -> bytes:
        try:
            async with self.http.stream(method, path, **kwargs) as response:  # type: ignore[arg-type]
                response.raise_for_status()
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > MAX_RESPONSE:
                        raise UpstreamError("Council response exceeded the allowed size.")
                return bytes(content)
        except httpx.HTTPError as exc:
            raise UpstreamError("Council service is unavailable; delivery will retry.") from exc

    async def submit(self, key: str, evidence: CouncilEvidence) -> UUID:
        from pydantic import BaseModel

        class Created(BaseModel):
            id: UUID

        try:
            data = await self.request(
                "POST",
                "/v1/assessments",
                headers={"Idempotency-Key": key},
                json=evidence.model_dump(mode="json"),
            )
            return Created.model_validate_json(data).id
        except (SchemaError, ValueError) as exc:
            raise UpstreamError("Council returned an invalid assessment identity.") from exc

    async def read(self, identity: UUID) -> RemoteAssessment:
        try:
            return RemoteAssessment.model_validate_json(
                await self.request("GET", f"/v1/assessments/{identity}")
            )
        except (SchemaError, ValueError) as exc:
            raise UpstreamError("Council returned an invalid assessment.") from exc

    async def retry(self, identity: UUID, key: str) -> None:
        await self.request(
            "POST", f"/v1/assessments/{identity}/retry", headers={"Idempotency-Key": key}
        )

    async def pdf(self, identity: UUID) -> bytes:
        content = await self.request("GET", f"/v1/assessments/{identity}/pdf")
        if not content.startswith(b"%PDF-"):
            raise UpstreamError("Council did not return a valid PDF artifact.")
        return content
