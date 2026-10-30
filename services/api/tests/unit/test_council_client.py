from uuid import uuid4

import httpx
import pytest

from app.core.errors import UpstreamError
from app.integrations.council import CouncilClient
from app.modules.council.schemas import CouncilEvidence


def evidence():
    return CouncilEvidence(
        title="Study", research_question="Does it work?", findings="Some findings."
    )


@pytest.mark.asyncio
async def test_client_auth_idempotency_and_failure_boundary():
    identity = uuid4()
    seen = []

    async def handler(request):
        seen.append(request)
        return httpx.Response(202, json={"id": str(identity), "status": "queued"})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://council.test",
        headers={"X-Council-Key": "secret"},
    ) as http:
        client = CouncilClient(http)
        assert await client.submit(str(identity), evidence()) == identity
        assert seen[0].headers["X-Council-Key"] == "secret"
        assert seen[0].headers["Idempotency-Key"] == str(identity)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(500)),
        base_url="https://council.test",
    ) as http:
        with pytest.raises(UpstreamError):
            await CouncilClient(http).submit(str(identity), evidence())


@pytest.mark.asyncio
async def test_pdf_rejects_wrong_content_and_oversize():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, content=b"not PDF")),
        base_url="https://council.test",
    ) as http:
        with pytest.raises(UpstreamError):
            await CouncilClient(http).pdf(uuid4())


def test_evidence_rejects_total_limits_and_unsafe_names():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CouncilEvidence(
            title="Study",
            research_question="?",
            findings="x",
            files=[{"name": "../secret.txt", "content": "x"}],
        )
    with pytest.raises(ValidationError):
        CouncilEvidence(
            title="Study",
            research_question="?",
            findings="x",
            files=[{"name": f"a{i}.txt", "content": "x" * 40000} for i in range(6)],
        )


@pytest.mark.asyncio
async def test_retry_sends_generation_key_and_preserves_conflicts():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(409, json={"detail": "Retry identity conflict."})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://council.test"
    ) as http:
        with pytest.raises(UpstreamError):
            await CouncilClient(http).retry(uuid4(), "durable-generation")
    assert seen[0].headers["Idempotency-Key"] == "durable-generation"
