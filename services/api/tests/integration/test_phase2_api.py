import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update

from app.core.roles import Role
from app.modules.audit.models import AuditEventRecord
from app.modules.auth.models import IdempotencyKey
from app.modules.files.models import MediaAsset, UploadIntent
from app.modules.problems.models import Report
from app.modules.users.models import User
from app.seeds.data import seed_id, user_id
from tests.integration.conftest import Phase2

pytestmark = pytest.mark.integration


def report_body(**values: object) -> dict[str, object]:
    return {
        "title": "Handpump repair",
        "transcript": "The handpump stopped working.",
        "summary": "No water from the handpump.",
        "category": "water",
        "severity": "high",
        "latitude": 16.76,
        "longitude": 77.14,
        "location_label": "Ward 4",
        "channel": "text",
        "media_ids": [],
        **values,
    }


async def uploaded(
    phase2: Phase2, role: Role = Role.CITIZEN, **metadata: object
) -> tuple[dict[str, object], dict[str, object]]:
    signed = await phase2.client.post(
        "/api/v1/media/signature",
        headers=phase2.headers(role),
        json={
            "filename": "before.jpg",
            "content_type": "image/jpeg",
            "bytes": 12345,
            "kind": "completion" if role == Role.OFFICER else "report",
        },
    )
    assert signed.status_code == 200, signed.text
    authorization = signed.json()
    public_id = authorization["parameters"]["public_id"]
    phase2.media.uploaded(public_id, **metadata)
    return authorization, {
        "upload_id": authorization["upload_id"],
        "public_id": public_id,
        "version": 123,
        "signature": "a" * 40,
    }


async def completed_media(phase2: Phase2, role: Role = Role.CITIZEN) -> str:
    _, complete = await uploaded(phase2, role)
    response = await phase2.client.post(
        "/api/v1/media/complete", headers=phase2.headers(role), json=complete
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


async def test_profile_uses_database_role_and_checks_disabled_and_unknown_accounts(
    phase2: Phase2,
) -> None:
    for role in Role:
        profile = await phase2.client.get("/api/v1/users/me", headers=phase2.headers(role))
        assert profile.status_code == 200, profile.text
        assert profile.json()["role"] == role
        assert profile.json()["id"] == str(user_id(role))
        expected = None if role == Role.SUPER_ADMIN else "Yadgir (demonstration)"
        assert profile.json()["district_name"] == expected
    assert (await phase2.client.get("/api/v1/users/me")).status_code == 401
    assert (
        await phase2.client.get("/api/v1/users/me", headers={"Authorization": "Bearer invalid"})
    ).status_code == 401
    assert (
        await phase2.client.get(
            "/api/v1/users/me", headers={"Authorization": "Bearer valid:unknown"}
        )
    ).status_code == 403
    async with phase2.sessions.begin() as session:
        await session.execute(
            update(User).where(User.id == user_id(Role.CITIZEN)).values(is_active=False)
        )
    assert (
        await phase2.client.get("/api/v1/users/me", headers=phase2.headers())
    ).status_code == 403


async def test_inactive_district_cannot_submit(phase2: Phase2) -> None:
    async with phase2.sessions.begin() as session:
        await session.execute(
            update(User)
            .where(User.id == user_id(Role.CITIZEN))
            .values(district_id=seed_id("district/boundary"))
        )
    response = await phase2.client.post(
        "/api/v1/reports",
        json=report_body(),
        headers=phase2.headers(**{"Idempotency-Key": "inactive-district"}),
    )
    assert response.status_code == 403


async def test_signed_upload_completion_replays_without_duplicating_or_rechecking_provider(
    phase2: Phase2,
) -> None:
    signed, body = await uploaded(phase2)
    assert all(isinstance(value, str) for value in signed["parameters"].values())
    assert signed["parameters"]["overwrite"] == "false"
    assert str(user_id(Role.CITIZEN)) in body["public_id"]
    responses = await asyncio.gather(
        *[
            phase2.client.post("/api/v1/media/complete", json=body, headers=phase2.headers())
            for _ in range(2)
        ]
    )
    assert all(response.status_code == 200 for response in responses)
    assert responses[0].json() == responses[1].json()
    assert phase2.media.calls == 1
    async with phase2.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(MediaAsset)) == 1
        intent = (await session.scalars(select(UploadIntent))).one()
        assert intent.completed_asset_id is not None


@pytest.mark.parametrize(
    "metadata",
    [
        {"format": "gif"},
        {"bytes": 10485761},
        {"resource_type": "video"},
        {"bytes": 1},
        {"public_id": "someone-elses-photo"},
        {"version": 999},
    ],
)
async def test_upload_completion_checks_actual_provider_metadata(
    phase2: Phase2, metadata: dict[str, object]
) -> None:
    _, body = await uploaded(phase2, **metadata)
    response = await phase2.client.post(
        "/api/v1/media/complete", json=body, headers=phase2.headers()
    )
    assert response.status_code == 422
    async with phase2.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(MediaAsset)) == 0


async def test_upload_failure_is_retryable_and_expired_intent_is_rejected(phase2: Phase2) -> None:
    signed, body = await uploaded(phase2)
    phase2.media.fail = True
    assert (
        await phase2.client.post("/api/v1/media/complete", json=body, headers=phase2.headers())
    ).status_code == 502
    phase2.media.fail = False
    assert (
        await phase2.client.post("/api/v1/media/complete", json=body, headers=phase2.headers())
    ).status_code == 200
    signed, body = await uploaded(phase2)
    async with phase2.sessions.begin() as session:
        await session.execute(
            update(UploadIntent)
            .where(UploadIntent.id == signed["upload_id"])
            .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
    response = await phase2.client.post(
        "/api/v1/media/complete", json=body, headers=phase2.headers()
    )
    assert response.status_code == 409


async def test_unowned_intent_and_tampered_signature_cannot_attach_assets(phase2: Phase2) -> None:
    _, body = await uploaded(phase2)
    assert (
        await phase2.client.post(
            "/api/v1/media/complete", json=body, headers=phase2.headers(Role.OFFICER)
        )
    ).status_code == 404
    response = await phase2.client.post(
        "/api/v1/media/complete", json={**body, "signature": "b" * 40}, headers=phase2.headers()
    )
    assert response.status_code == 422
    response = await phase2.client.post(
        "/api/v1/media/complete",
        json={**body, "public_id": "stolen/asset"},
        headers=phase2.headers(),
    )
    assert response.status_code == 403
    assert phase2.media.calls == 0


async def test_upload_kind_is_role_restricted(phase2: Phase2) -> None:
    for role, kind in (
        (Role.CITIZEN, "completion"),
        (Role.OFFICER, "report"),
        (Role.STUDENT, "report"),
    ):
        response = await phase2.client.post(
            "/api/v1/media/signature",
            headers=phase2.headers(role),
            json={"filename": "test.jpg", "content_type": "image/jpeg", "bytes": 100, "kind": kind},
        )
        assert response.status_code == 403
    for changes in ({"bytes": 10485761}, {"bytes": True}, {"content_type": "image/gif"}):
        response = await phase2.client.post(
            "/api/v1/media/signature",
            headers=phase2.headers(),
            json={
                "filename": "test.jpg",
                "content_type": "image/jpeg",
                "bytes": 100,
                "kind": "report",
                **changes,
            },
        )
        assert response.status_code == 422


async def test_report_photo_persist_across_new_app_and_session_and_retry_is_identical(
    phase2: Phase2,
) -> None:
    media_id = await completed_media(phase2)
    body = report_body(media_ids=[media_id])
    headers = phase2.headers(**{"Idempotency-Key": "create-once"})
    created = await phase2.client.post("/api/v1/reports", json=body, headers=headers)
    assert created.status_code == 201, created.text
    saved = created.json()
    assert saved["reporter_id"] == str(user_id(Role.CITIZEN))
    assert saved["status"] == "reported" and saved["status_changed_at"]
    assert saved["media"][0]["id"] == media_id
    assert saved["media"][0]["thumbnail_url"].startswith("https://res.cloudinary.com/")
    replay = await phase2.client.post("/api/v1/reports", json=body, headers=headers)
    assert replay.status_code == 201 and replay.json() == saved
    conflict = await phase2.client.post(
        "/api/v1/reports", json={**body, "title": "Different"}, headers=headers
    )
    assert conflict.status_code == 409
    detail = await phase2.client.get(f"/api/v1/reports/{saved['id']}", headers=phase2.headers())
    assert detail.status_code == 200 and detail.json() == saved
    listing = await phase2.client.get("/api/v1/reports?mine=true", headers=phase2.headers())
    assert saved in listing.json()["items"]
    # A separate application and request session simulate lost in-memory state;
    # the fixtures' provider boundaries are reapplied, not business state.
    import httpx

    from app.core.database import get_db
    from app.integrations.cloudinary import get_media_provider
    from app.main import create_app

    restart = create_app()
    restart.state.authenticator = phase2.app.state.authenticator
    restart.dependency_overrides[get_db] = phase2.app.dependency_overrides[get_db]
    restart.dependency_overrides[get_media_provider] = lambda: phase2.media
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=restart), base_url="http://restart"
    ) as client:
        response = await client.get(f"/api/v1/reports/{saved['id']}", headers=phase2.headers())
        assert response.status_code == 200 and response.json() == saved


async def test_concurrent_report_retry_creates_one_report_and_one_audit_event(
    phase2: Phase2,
) -> None:
    media_id = await completed_media(phase2)
    responses = await asyncio.gather(
        *[
            phase2.client.post(
                "/api/v1/reports",
                json=report_body(media_ids=[media_id]),
                headers=phase2.headers(**{"Idempotency-Key": "concurrent"}),
            )
            for _ in range(2)
        ]
    )
    assert [response.status_code for response in responses] == [201, 201]
    assert responses[0].json() == responses[1].json()
    async with phase2.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Report)) == 4
        assert await session.scalar(select(func.count()).select_from(IdempotencyKey)) == 1
        assert (
            await session.scalar(
                select(func.count())
                .select_from(AuditEventRecord)
                .where(AuditEventRecord.action == "report.created")
            )
            == 1
        )


async def test_different_requests_cannot_consume_one_photo_twice(phase2: Phase2) -> None:
    media_id = await completed_media(phase2)
    responses = await asyncio.gather(
        *[
            phase2.client.post(
                "/api/v1/reports",
                json=report_body(media_ids=[media_id]),
                headers=phase2.headers(**{"Idempotency-Key": key}),
            )
            for key in ("first", "second")
        ]
    )
    assert sorted(response.status_code for response in responses) == [201, 422]
    async with phase2.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Report)) == 4
        assert await session.scalar(select(func.count()).select_from(IdempotencyKey)) == 1


async def test_citizen_ownership_limits_reads_and_media_attachments(phase2: Phase2) -> None:
    media_id = await completed_media(phase2)
    async with phase2.sessions.begin() as session:
        session.add(
            User(
                id=uuid4(),
                firebase_uid="another-citizen",
                email="other@example.test",
                display_name="Other citizen",
                role=Role.CITIZEN,
                district_id=seed_id("district/yadgir"),
                is_active=True,
            )
        )
    other = {"Authorization": "Bearer valid:another-citizen"}
    assert (
        await phase2.client.get(f"/api/v1/reports/{seed_id('report/reported')}", headers=other)
    ).status_code == 404
    assert (await phase2.client.get("/api/v1/reports?mine=true", headers=other)).json() == {
        "items": []
    }
    response = await phase2.client.post(
        "/api/v1/reports",
        json=report_body(media_ids=[media_id]),
        headers={**other, "Idempotency-Key": "steal"},
    )
    assert response.status_code == 422
    completion = await completed_media(phase2, Role.OFFICER)
    response = await phase2.client.post(
        "/api/v1/reports",
        json=report_body(media_ids=[completion]),
        headers=phase2.headers(**{"Idempotency-Key": "wrong-kind"}),
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "changes",
    [
        {"reporter_id": str(uuid4())},
        {"district_id": str(uuid4())},
        {"latitude": True},
        {"latitude": 91},
        {"longitude": "77.14"},
        {"title": " "},
        {"category": "unknown"},
        {"media_ids": [str(uuid4())] * 4},
    ],
)
async def test_invalid_report_body_never_creates_a_record(
    phase2: Phase2, changes: dict[str, object]
) -> None:
    response = await phase2.client.post(
        "/api/v1/reports",
        json=report_body(**changes),
        headers=phase2.headers(**{"Idempotency-Key": "invalid"}),
    )
    assert response.status_code == 422
    async with phase2.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Report)) == 3


@pytest.mark.parametrize("channel", ["text", "voice", "photo", "location"])
async def test_every_citizen_app_channel_is_accepted_and_saved(
    phase2: Phase2, channel: str
) -> None:
    response = await phase2.client.post(
        "/api/v1/reports",
        headers={**phase2.headers(), "Idempotency-Key": f"channel-{channel}"},
        json=report_body(channel=channel),
    )
    assert response.status_code == 201, response.text
    assert response.json()["channel"] == channel
    async with phase2.sessions() as session:
        saved = await session.get(Report, response.json()["id"])
        assert saved.channel == channel


async def test_unknown_channel_is_still_refused(phase2: Phase2) -> None:
    response = await phase2.client.post(
        "/api/v1/reports",
        headers={**phase2.headers(), "Idempotency-Key": "channel-sms"},
        json=report_body(channel="sms"),
    )
    assert response.status_code == 422
