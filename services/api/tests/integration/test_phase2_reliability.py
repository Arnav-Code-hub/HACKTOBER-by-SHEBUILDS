from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import func, select, update

from app.core.database import get_db
from app.core.roles import Role
from app.modules.auth.models import IdempotencyKey
from app.modules.files.models import UploadIntent
from app.modules.problems.models import Report
from app.modules.users.models import User
from app.seeds.data import seed_id, user_id
from tests.integration.conftest import Phase2
from tests.integration.test_phase2_api import report_body, uploaded

pytestmark = pytest.mark.integration


async def test_timely_upload_can_be_completed_after_an_api_outage(phase2: Phase2) -> None:
    signed, body = await uploaded(phase2)
    now = datetime.now(UTC)
    phase2.media.assets[body["public_id"]]["created_at"] = (now - timedelta(minutes=20)).isoformat()
    async with phase2.sessions.begin() as session:
        await session.execute(
            update(UploadIntent)
            .where(UploadIntent.id == signed["upload_id"])
            .values(created_at=now - timedelta(minutes=30), expires_at=now - timedelta(minutes=15))
        )
    response = await phase2.client.post(
        "/api/v1/media/complete", json=body, headers=phase2.headers()
    )
    assert response.status_code == 200, response.text


async def test_commit_failure_returns_error_and_rolls_back_report(phase2: Phase2) -> None:
    async def failing_commit():
        async with phase2.sessions() as session:
            try:
                yield session
                raise RuntimeError("simulated commit failure")
            finally:
                await session.rollback()

    phase2.app.dependency_overrides[get_db] = failing_commit
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=phase2.app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/reports",
            json=report_body(),
            headers=phase2.headers(**{"Idempotency-Key": "commit-failed"}),
        )
    assert response.status_code == 500
    async with phase2.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Report)) == 3
        assert await session.scalar(select(func.count()).select_from(IdempotencyKey)) == 0


async def test_scope_cannot_reuse_a_district_id_as_a_department_id(phase2: Phase2) -> None:
    async with phase2.sessions.begin() as session:
        await session.execute(
            update(User)
            .where(User.id == user_id(Role.DEPARTMENT))
            .values(department_id=seed_id("district/yadgir"))
        )
    response = await phase2.client.get("/api/v1/users/me", headers=phase2.headers(Role.DEPARTMENT))
    assert response.status_code == 403
