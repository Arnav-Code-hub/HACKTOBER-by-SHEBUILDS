"""Phase 7: optional report suggestions. Gemini is always faked."""

import asyncio
import json
from time import monotonic
from typing import Any

import pytest
from sqlalchemy import func, select

from app.core.config import Settings, get_settings
from app.core.database import Base
from app.core.roles import Role
from app.integrations.gemini import get_suggestion_provider
from app.modules.problems.suggestions import RESPONSE_SCHEMA, UNAVAILABLE
from tests.integration.conftest import Phase2
from tests.integration.test_phase2_api import report_body
from tests.integration.test_phase4_api import add_user

pytestmark = pytest.mark.integration
PATH = "/api/v1/reports/suggest"
VALID = {
    "category": "water",
    "severity": "high",
    "title": "Handpump not working",
    "summary": "The ward 4 handpump gives no water.",
    "mentioned_location": "Ward 4",
    "detected_language": "en",
}


class FakeSuggestions:
    def __init__(self) -> None:
        self.reply: str | None = json.dumps(VALID)
        self.delay = 0.0
        self.error: Exception | None = None
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def suggest(self, transcript: str, schema: dict[str, Any]) -> str | None:
        self.calls.append((transcript, schema))
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return self.reply


def settings(**values: object) -> Settings:
    configured: dict[str, object] = {
        "gemini_api_key": "test-key",
        "gemini_model": "test-model",
        "gemini_timeout_seconds": 1,
        **values,
    }
    return Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://user:pass@localhost:5432/unused",
        **configured,
    )


@pytest.fixture
def gemini(phase2: Phase2) -> FakeSuggestions:
    fake = FakeSuggestions()
    phase2.app.dependency_overrides[get_suggestion_provider] = lambda: fake
    # A lambda: FastAPI would read settings()'s **values as request parameters.
    phase2.app.dependency_overrides[get_settings] = lambda: settings()
    return fake


async def suggest(phase2: Phase2, transcript: object = "  Handpump broken in ward 4  ", **h):
    return await phase2.client.post(
        PATH, json={"transcript": transcript}, headers=h or phase2.headers()
    )


async def row_counts(phase2: Phase2) -> dict[str, int]:
    async with phase2.sessions() as session:
        return {
            table.name: await session.scalar(select(func.count()).select_from(table)) or 0
            for table in Base.metadata.sorted_tables
        }


async def test_valid_suggestion_returns_the_contract_and_writes_nothing(
    phase2: Phase2, gemini: FakeSuggestions
) -> None:
    before = await row_counts(phase2)
    response = await suggest(phase2)
    assert response.status_code == 200, response.text
    assert response.json() == VALID
    # The stripped transcript and the inlined schema reach the provider.
    assert gemini.calls == [("Handpump broken in ward 4", RESPONSE_SCHEMA)]
    assert await row_counts(phase2) == before


async def test_no_location_is_null(phase2: Phase2, gemini: FakeSuggestions) -> None:
    gemini.reply = json.dumps({**VALID, "mentioned_location": None})
    response = await suggest(phase2)
    assert response.status_code == 200 and response.json()["mentioned_location"] is None


@pytest.mark.parametrize(
    "reply",
    [
        None,
        "",
        "not json",
        "[]",
        json.dumps({**VALID, "category": "parks"}),
        json.dumps({**VALID, "severity": "urgent"}),
        json.dumps({**VALID, "detected_language": "fr"}),
        json.dumps({key: value for key, value in VALID.items() if key != "title"}),
        json.dumps({**VALID, "status": "funded"}),
        json.dumps({**VALID, "title": "x" * 121}),
        json.dumps({**VALID, "summary": "   "}),
        json.dumps({**VALID, "mentioned_location": "x" * 201}),
    ],
)
async def test_malformed_output_is_503(
    phase2: Phase2, gemini: FakeSuggestions, reply: str | None
) -> None:
    gemini.reply = reply
    response = await suggest(phase2)
    assert response.status_code == 503, response.text
    assert response.json() == {"detail": UNAVAILABLE}


async def test_timeout_is_503_within_the_limit(phase2: Phase2, gemini: FakeSuggestions) -> None:
    gemini.delay = 5
    started = monotonic()
    response = await suggest(phase2)
    assert response.status_code == 503
    assert monotonic() - started < 3


async def test_provider_errors_are_503_without_their_text(
    phase2: Phase2, gemini: FakeSuggestions
) -> None:
    gemini.error = RuntimeError("quota exceeded for key test-key")
    response = await suggest(phase2)
    assert response.status_code == 503
    assert response.json() == {"detail": UNAVAILABLE}


@pytest.mark.parametrize("missing", ["gemini_api_key", "gemini_model"])
async def test_unconfigured_is_503_without_a_provider_call(
    phase2: Phase2, gemini: FakeSuggestions, missing: str
) -> None:
    phase2.app.dependency_overrides[get_settings] = lambda: settings(**{missing: " "})
    response = await suggest(phase2)
    assert response.status_code == 503
    assert response.json() == {"detail": "Suggestions are not configured"}
    assert gemini.calls == []


@pytest.mark.parametrize(
    "role", [Role.PANCHAYAT, Role.DEPARTMENT, Role.OFFICER, Role.STUDENT, Role.SUPER_ADMIN]
)
async def test_only_citizens_may_ask(phase2: Phase2, gemini: FakeSuggestions, role: Role) -> None:
    assert (await suggest(phase2, **phase2.headers(role))).status_code == 403
    assert gemini.calls == []


@pytest.mark.parametrize("transcript", ["", "   ", "x" * 2001, 42])
async def test_invalid_transcripts_are_422(
    phase2: Phase2, gemini: FakeSuggestions, transcript: object
) -> None:
    assert (await suggest(phase2, transcript)).status_code == 422
    assert gemini.calls == []


async def test_unknown_fields_are_422(phase2: Phase2, gemini: FakeSuggestions) -> None:
    response = await phase2.client.post(
        PATH, json={"transcript": "Broken", "photos": []}, headers=phase2.headers()
    )
    assert response.status_code == 422


async def test_rate_limit_is_per_user(phase2: Phase2, gemini: FakeSuggestions) -> None:
    for _ in range(10):
        assert (await suggest(phase2)).status_code == 200
    limited = await suggest(phase2)
    assert limited.status_code == 429
    assert len(gemini.calls) == 10
    other = await add_user(phase2, "other-citizen", Role.CITIZEN)
    assert (await suggest(phase2, **other)).status_code == 200


async def test_report_creation_works_while_suggestions_fail(
    phase2: Phase2, gemini: FakeSuggestions
) -> None:
    gemini.error = RuntimeError("Gemini is down")
    assert (await suggest(phase2)).status_code == 503
    created = await phase2.client.post(
        "/api/v1/reports",
        json=report_body(),
        headers=phase2.headers(**{"Idempotency-Key": "while-suggestions-fail"}),
    )
    assert created.status_code == 201, created.text
