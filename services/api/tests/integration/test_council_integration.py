"""Real PostgreSQL delivery acceptance; run with the existing isolated phase2 fixture."""

import asyncio
import base64
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.errors import UpstreamError
from app.core.roles import Role
from app.core.security import get_current_principal
from app.modules.auth.models import IdempotencyKey
from app.modules.council.models import CouncilAssessment
from app.modules.council.schemas import RemoteAssessment
from app.modules.notifications.models import Notification
from app.persistence import council, council_worker
from app.persistence.council import advance
from app.seeds.data import seed_id, user_id
from tests.integration.helpers import demo_principal

pytestmark = pytest.mark.integration


@pytest.fixture
def council_enabled(monkeypatch):
    monkeypatch.setenv("COUNCIL_ENABLED", "true")
    monkeypatch.setenv("COUNCIL_URL", "http://127.0.0.1:8090")
    monkeypatch.setenv("COUNCIL_SERVICE_KEY", "test-only-" + "x" * 40)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def completed_remote(identity, evidence):
    return RemoteAssessment.model_validate(
        {
            "id": str(identity),
            "status": "completed",
            "completed_reviewers": 5,
            "project": evidence,
            "report": {
                "version": "1.0",
                "simulated": False,
                "model": "test-model",
                "prompt_version": "1.0",
                "summary": "Advisory only.",
                "reviewers": [
                    {
                        "reviewer": name,
                        "strengths": [],
                        "issues": [],
                        "limitations": ["Only supplied evidence assessed."],
                    }
                    for name in ["evidence", "engineer", "sceptic", "impact", "delivery"]
                ],
                "priorities": [],
                "limitations": ["Faculty retain judgment."],
            },
        }
    )


@pytest.fixture
async def supervised_submission(phase2, council_enabled):
    assignment = await phase2.client.post(
        f"/api/v1/council/teams/{seed_id('team')}/supervisor",
        json={"faculty_id": str(user_id(Role.FACULTY))},
        headers=phase2.headers(Role.INSTITUTE),
    )
    assert assignment.status_code == 200, assignment.text
    return f"/api/v1/council/submissions/{seed_id('submission')}/assessments", {
        "title": "Pump study",
        "research_question": "Do alerts reduce downtime?",
        "findings": "Some users reported fewer outages.",
    }


@pytest.fixture
async def delivery(phase2, supervised_submission, monkeypatch):
    path, body = supervised_submission
    created = await phase2.client.post(
        path,
        json=body,
        headers=phase2.headers(Role.STUDENT, **{"Idempotency-Key": "council-delivery"}),
    )
    assert created.status_code == 202, created.text
    identity = UUID(created.json()["id"])
    async with phase2.sessions() as session:
        row = await session.get(CouncilAssessment, identity)
        remote = completed_remote(uuid4(), row.evidence)
    client = SimpleNamespace(
        submit=AsyncMock(return_value=remote.id),
        read=AsyncMock(return_value=remote),
        pdf=AsyncMock(return_value=b"%PDF-canonical-council-report"),
        retry=AsyncMock(),
    )
    monkeypatch.setattr(council_worker, "SessionLocal", phase2.sessions)
    return identity, client


async def test_supervised_report_is_published_privately_and_idempotently(phase2, council_enabled):
    body = {
        "title": "Pump study",
        "research_question": "Do alerts reduce downtime?",
        "findings": "Some users reported fewer outages.",
    }
    path = f"/api/v1/council/submissions/{seed_id('submission')}/assessments"
    headers = phase2.headers(Role.STUDENT, **{"Idempotency-Key": "council-first"})
    missing = await phase2.client.post(path, json=body, headers=headers)
    assert missing.status_code == 409, missing.text
    assignment = await phase2.client.post(
        f"/api/v1/council/teams/{seed_id('team')}/supervisor",
        json={"faculty_id": str(user_id(Role.FACULTY))},
        headers=phase2.headers(Role.INSTITUTE),
    )
    assert assignment.status_code == 200, assignment.text
    created = await phase2.client.post(path, json=body, headers=headers)
    assert created.status_code == 202, created.text
    assert (await phase2.client.post(path, json=body, headers=headers)).json() == created.json()
    conflict = await phase2.client.post(
        path, json={**body, "findings": "Different"}, headers=headers
    )
    assert conflict.status_code == 409
    identity = UUID(created.json()["id"])
    remote_id = uuid4()
    async with phase2.sessions.begin() as session:
        row = await session.get(CouncilAssessment, identity, with_for_update=True)
        remote = completed_remote(remote_id, row.evidence)
        client = SimpleNamespace(
            submit=AsyncMock(return_value=remote_id),
            read=AsyncMock(return_value=remote),
            pdf=AsyncMock(return_value=b"%PDF-canonical-council-report"),
        )
        await advance(session, row, client, get_settings())
        assert row.status == "available"
    for role in [Role.STUDENT, Role.FACULTY]:
        pdf = await phase2.client.get(
            f"/api/v1/council/assessments/{identity}/pdf", headers=phase2.headers(role)
        )
        assert pdf.status_code == 200, pdf.text
        assert base64.b64decode(pdf.json()["content_base64"]) == b"%PDF-canonical-council-report"
        assert pdf.headers["cache-control"] == "private, no-store"
    async with phase2.sessions() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(Notification)
                .where(
                    Notification.resource_id == identity,
                    Notification.event_key == "council.completed",
                )
            )
            == 2
        )
    for principal in [
        replace(demo_principal(Role.FACULTY), user_id=uuid4()),
        replace(demo_principal(Role.STUDENT), institute_id=uuid4()),
        demo_principal(Role.INSTITUTE),
    ]:
        phase2.app.dependency_overrides[get_current_principal] = lambda p=principal: p
        denied = await phase2.client.get(f"/api/v1/council/assessments/{identity}/pdf")
        assert denied.status_code in {403, 404}, denied.text
    phase2.app.dependency_overrides.pop(get_current_principal, None)


async def test_concurrent_same_key_requests_persist_one_assessment(phase2, supervised_submission):
    path, body = supervised_submission
    key = "council-concurrent"
    responses = await asyncio.gather(
        *(
            phase2.client.post(
                path,
                json=body,
                headers=phase2.headers(Role.STUDENT, **{"Idempotency-Key": key}),
            )
            for _ in range(4)
        )
    )
    for response in responses:
        assert response.status_code == 202, response.text
        assert response.json() == responses[0].json()
    identity = UUID(responses[0].json()["id"])
    async with phase2.sessions() as session:
        assessments = list(await session.scalars(select(CouncilAssessment)))
        assert [row.id for row in assessments] == [identity]
        keys = list(
            await session.scalars(
                select(IdempotencyKey).where(
                    IdempotencyKey.user_id == user_id(Role.STUDENT),
                    IdempotencyKey.operation == "council.assess",
                    IdempotencyKey.key == key,
                )
            )
        )
        assert len(keys) == 1
        assert keys[0].response_json == responses[0].json()


async def test_pdf_delivery_retry_reuses_the_completed_upstream_assessment(phase2, delivery):
    identity, client = delivery
    canonical_pdf = b"%PDF-canonical-council-report"
    client.pdf.side_effect = [UpstreamError("PDF temporarily unavailable."), canonical_pdf]
    assert await council_worker.poll_once(get_settings(), client)
    async with phase2.sessions() as session:
        row = await session.get(CouncilAssessment, identity)
        assert row.status == "delivery_failed"
        assert row.remote_id == client.submit.return_value
        assert row.report is None and row.pdf is None and row.delivered_at is None
        assert (
            await session.scalar(
                select(func.count())
                .select_from(Notification)
                .where(Notification.resource_id == identity)
            )
            == 0
        )
    path = f"/api/v1/council/assessments/{identity}"
    headers = phase2.headers(Role.STUDENT)
    detail = await phase2.client.get(path, headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["report"] is None
    assert (await phase2.client.get(path + "/pdf", headers=headers)).status_code == 409
    retried = await phase2.client.post(path + "/retry", headers=headers)
    assert retried.status_code == 200, retried.text
    assert await council_worker.poll_once(get_settings(), client)
    async with phase2.sessions() as session:
        row = await session.get(CouncilAssessment, identity)
        assert row.status == "available"
        assert row.remote_id == client.submit.return_value
        assert row.report == client.read.return_value.report.model_dump(mode="json")
        assert row.pdf == canonical_pdf and row.delivered_at is not None
        assert (
            await session.scalar(
                select(func.count())
                .select_from(Notification)
                .where(Notification.resource_id == identity)
            )
            == 2
        )
    pdf = await phase2.client.get(path + "/pdf", headers=headers)
    assert pdf.status_code == 200, pdf.text
    assert base64.b64decode(pdf.json()["content_base64"]) == canonical_pdf
    assert client.submit.await_count == 1
    client.retry.assert_not_awaited()
    assert [call.args for call in client.pdf.await_args_list] == [
        (client.submit.return_value,),
        (client.submit.return_value,),
    ]
    assert not await council_worker.poll_once(get_settings(), client)


async def test_notification_failure_rolls_back_publication(phase2, delivery, monkeypatch):
    identity, client = delivery
    publish = council.publish_case_update

    async def fail_after_notifications(session, *args, **kwargs):
        await publish(session, *args, **kwargs)
        await session.flush()
        assert (
            await session.scalar(
                select(func.count())
                .select_from(Notification)
                .where(Notification.resource_id == identity)
            )
            == 2
        )
        raise RuntimeError("Notification delivery interrupted.")

    monkeypatch.setattr(council, "publish_case_update", fail_after_notifications)
    with pytest.raises(RuntimeError, match="Notification delivery interrupted"):
        await council_worker.poll_once(get_settings(), client)
    async with phase2.sessions() as session:
        row = await session.get(CouncilAssessment, identity)
        assert row.status == "queued"
        assert row.remote_id is None and row.completed_reviewers == 0
        assert row.report is None and row.pdf is None and row.delivered_at is None
        assert (
            await session.scalar(
                select(func.count())
                .select_from(Notification)
                .where(Notification.resource_id == identity)
            )
            == 0
        )
    path = f"/api/v1/council/assessments/{identity}"
    for role in [Role.STUDENT, Role.FACULTY]:
        headers = phase2.headers(role)
        detail = await phase2.client.get(path, headers=headers)
        assert detail.status_code == 200, detail.text
        assert detail.json()["status"] == "queued" and detail.json()["report"] is None
        assert (await phase2.client.get(path + "/pdf", headers=headers)).status_code == 409
