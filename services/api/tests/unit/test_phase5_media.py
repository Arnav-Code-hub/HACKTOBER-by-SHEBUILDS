import base64
import hashlib
from dataclasses import replace
from datetime import UTC, datetime
from urllib.parse import unquote, urlsplit

import httpx
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.evidence import CardPhoto, EvidenceCard
from app.integrations.cloudinary import CloudinaryMediaProvider
from app.integrations.measurement import BROWSER_ACCEPT, measure_asset, measure_body
from app.modules.problems.schemas import VerifyWorkOrder
from tests.integration.phase2_fakes import MediaProvider

PHOTO = CardPhoto("janmaang/users/reporter/report/before", 123, datetime(2026, 10, 21, tzinfo=UTC))
AFTER = CardPhoto(
    "janmaang/users/officer/completion/after", 456, datetime(2026, 10, 24, tzinfo=UTC)
)


def provider() -> CloudinaryMediaProvider:
    return CloudinaryMediaProvider(
        Settings(
            _env_file=None,
            cloudinary_cloud_name="test-cloud",
            cloudinary_api_key="public-key",
            cloudinary_api_secret="server-secret",
        )
    )


def valid_signature(url: str) -> bool:
    # The installed SDK signs transformation/public_id, excluding the cache
    # version path, with a 32-character SHA-256 URL signature in long mode.
    path = urlsplit(url).path.split("/image/upload/", 1)[1]
    signature, transformed = path.split("/", 1)
    transformation, source = transformed.rsplit("/v123/", 1)
    signed = f"{transformation}/{source}server-secret".encode()
    expected = base64.urlsafe_b64encode(hashlib.sha256(signed).digest()).decode()[:32]
    return signature == f"s--{expected}--"


def test_panels_preserve_aspect_ratio_on_equal_canvases() -> None:
    url = provider().panel(PHOTO.public_id, PHOTO.version)
    assert url.startswith("https://res.cloudinary.com/test-cloud/image/upload/s--")
    assert all(
        value in url for value in ["c_pad", "w_640", "h_480", "g_center", "f_auto", "q_auto"]
    )
    assert "c_fill" not in url and "server-secret" not in url


def test_card_uses_image_and_text_layers_and_signs_the_entire_composition() -> None:
    pending = EvidenceCard("JM-123", PHOTO, AFTER, 1, "Awaiting citizen verification")
    url = provider().evidence_card(pending)
    readable = unquote(url)
    assert "l_janmaang:users:officer:completion:after" in readable
    assert "l_text:Arial_" in readable and "Awaiting citizen verification" in readable
    assert "Before - 2026-10-21" in readable and "After - round 1 - 2026-10-24" in readable
    assert "c_lpad" in readable and "w_1280" in readable and "h_640" in readable
    assert "c_fill" not in readable and "server-secret" not in readable
    assert valid_signature(url)
    edited = url.replace("Awaiting%20citizen%20verification", "Citizen%20verified")
    assert edited != url and not valid_signature(edited)
    confirmed = provider().evidence_card(replace(pending, verdict_label="Citizen verified"))
    assert confirmed != url and valid_signature(confirmed)


def test_card_without_before_uses_an_honest_text_panel() -> None:
    url = provider().evidence_card(EvidenceCard("JM-123", None, AFTER, 1, "Citizen verified"))
    assert "No original photo attached" in unquote(url)
    assert url.endswith("/v456/" + AFTER.public_id)
    assert "g_south_east" in url


@pytest.mark.parametrize(
    "public_id", ["https://example.test/photo", "fetch:evil", "../outside", "photo,ar_1"]
)
def test_card_rejects_arbitrary_url_or_transformation_references(public_id: str) -> None:
    with pytest.raises(ValueError):
        provider().evidence_card(
            EvidenceCard(
                "JM-123", PHOTO, replace(AFTER, public_id=public_id), 1, "Citizen verified"
            )
        )


@pytest.mark.parametrize(
    "body",
    [
        {"verdict": 1, "expected_round": 1},
        {"verdict": "true", "expected_round": 1},
        {"verdict": True, "expected_round": True},
        {"verdict": True, "expected_round": "1"},
        {"verdict": True, "expected_round": 0},
        {"verdict": True},
        {"verdict": True, "expected_round": 1, "comment": "x" * 501},
    ],
)
def test_verdict_requires_a_boolean_and_explicit_positive_integer_round(
    body: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        VerifyWorkOrder.model_validate(body)


async def test_measurement_uses_real_response_lengths_and_preserves_negative_savings() -> None:
    media = MediaProvider()
    media.uploaded(PHOTO.public_id, bytes=100)
    seen = []

    def respond(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers)
        return httpx.Response(200, content=b"x" * 120, headers={"content-type": "image/webp"})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = await measure_asset(media, client, PHOTO.public_id, folder="janmaang")
    assert result["original_bytes"] == 100
    assert all(variant["delivered_bytes"] == 120 for variant in result["variants"])
    assert all(variant["savings_percent"] == pytest.approx(-20) for variant in result["variants"])
    assert all(
        headers["accept"] == BROWSER_ACCEPT and headers["accept-encoding"] == "identity"
        for headers in seen
    )


@pytest.mark.parametrize(("status", "content_type"), [(403, "image/png"), (200, "text/html")])
def test_measurement_never_reports_provider_failures_as_optimized_images(
    status: int, content_type: str
) -> None:
    with (
        httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    status, content=b"failure", headers={"content-type": content_type}
                )
            )
        ) as client,
        pytest.raises((httpx.HTTPStatusError, ValueError)),
    ):
        measure_body(
            client, "https://res.cloudinary.com/test/image/upload/image", accept=BROWSER_ACCEPT
        )
