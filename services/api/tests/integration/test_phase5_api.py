"""Real PostgreSQL verdict transactions; only external providers are doubled."""

import asyncio
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import func, select, update

from app.core.database import get_db
from app.core.roles import Role
from app.modules.audit.models import AuditEventRecord
from app.modules.auth.models import IdempotencyKey
from app.modules.files.models import MediaAsset
from app.modules.funding.models import Allocation
from app.modules.problems.models import Cluster, Verification, WorkOrder
from app.seeds.data import seed_id
from tests.integration.conftest import Phase2
from tests.integration.helpers import new_report
from tests.integration.test_phase2_api import completed_media, report_body
from tests.integration.test_phase4_api import add_user, other_department

pytestmark = pytest.mark.integration
ORDER = seed_id("work-order")
ANCHOR = seed_id("report/in_progress")
CLUSTER = seed_id("cluster/in_progress")


async def completion(phase2: Phase2, order=ORDER, key="complete-phase5", round_=1) -> str:
    photo_id = await completed_media(phase2, Role.OFFICER)
    response = await phase2.client.post(
        f"/api/v1/work-orders/{order}/complete",
        json={"media_ids": [photo_id], "expected_round": round_},
        headers=phase2.headers(Role.OFFICER, **{"Idempotency-Key": key}),
    )
    assert response.status_code == 200, response.text
    return photo_id


async def ready(phase2: Phase2, *, before: bool = True) -> str:
    if before:
        photo = await completed_media(phase2)
        async with phase2.sessions.begin() as session:
            await session.execute(
                update(MediaAsset).where(MediaAsset.id == UUID(photo)).values(report_id=ANCHOR)
            )
    return await completion(phase2)


async def view(phase2: Phase2, report_id=ANCHOR, headers=None):
    response = await phase2.client.get(
        f"/api/v1/reports/{report_id}/verification", headers=headers or phase2.headers()
    )
    assert response.status_code == 200, response.text
    return response.json()


async def verdict(
    phase2: Phase2,
    value: bool,
    *,
    round_=1,
    key="verdict-phase5",
    order=ORDER,
    headers=None,
    **extra,
):
    return await phase2.client.post(
        f"/api/v1/work-orders/{order}/verify",
        json={"verdict": value, "expected_round": round_, **extra},
        headers={**(headers or phase2.headers()), "Idempotency-Key": key},
    )


async def test_view_and_card_share_selected_evidence_then_confirmed_status(phase2: Phase2) -> None:
    after_id = await ready(phase2)
    pending = await view(phase2)
    assert pending["status"] == "awaiting_verification" and pending["can_verify"]
    assert pending["round"] == pending["after_round"] == 1 and pending["blocked_reason"] is None
    assert pending["before"]["url"].startswith("https://res.cloudinary.com/")
    assert "/panel/" in pending["after"]["url"]
    officer = (
        await phase2.client.get(
            f"/api/v1/work-orders/{ORDER}/evidence", headers=phase2.headers(Role.OFFICER)
        )
    ).json()
    assert {name: pending[name] for name in officer} == officer
    assert phase2.media.cards[-1].verdict_label == "Awaiting citizen verification"
    async with phase2.sessions() as session:
        assert (
            phase2.media.cards[-1].after.public_id
            == (await session.get(MediaAsset, UUID(after_id))).public_id
        )
    saved = await verdict(phase2, True, comment="  Water flows again.  ")
    assert saved.status_code == 200 and saved.json()["status"] == "citizen_verified"
    confirmed = await view(phase2)
    assert not confirmed["can_verify"] and "already confirmed" in confirmed["blocked_reason"]
    assert confirmed["verdict_label"] == "Citizen verified"
    assert confirmed["card_url"] != pending["card_url"]
    assert confirmed["after"] == pending["after"]
    detail = (await phase2.client.get(f"/api/v1/reports/{ANCHOR}", headers=phase2.headers())).json()
    assert detail["status"] == "citizen_verified"
    async with phase2.sessions() as session:
        recorded = (await session.scalars(select(Verification))).one()
        assert recorded.round == 1 and recorded.verdict and recorded.comment == "Water flows again."
        audit = (
            await session.scalars(
                select(AuditEventRecord)
                .where(
                    AuditEventRecord.entity_id == CLUSTER,
                    AuditEventRecord.action == "cluster.status_changed",
                )
                .order_by(AuditEventRecord.created_at.desc())
            )
        ).first()
        assert audit.after["status"] == "citizen_verified" and audit.after["verdict"] is True
        assert audit.before["round"] == audit.after["round"] == 1
        assert await session.scalar(select(func.count()).select_from(Allocation)) == 1


async def test_negative_verdict_keeps_returned_photo_and_allocation_until_round_two(
    phase2: Phase2,
) -> None:
    await ready(phase2)
    original = await view(phase2)
    response = await verdict(phase2, False, comment="Still dry.")
    assert response.status_code == 200 and response.json()["status"] == "in_progress"
    returned = await view(phase2)
    assert returned["round"] == 2 and returned["after_round"] == 1
    assert not returned["can_verify"] and "correction" in returned["blocked_reason"]
    assert returned["after"] == original["after"]
    assert returned["verdict_label"] == "Round 1 · returned for correction"
    assert phase2.media.cards[-1].after_round == 1
    assert phase2.media.cards[-1].verdict_label == returned["verdict_label"]
    officer = (
        await phase2.client.get(
            f"/api/v1/work-orders/{ORDER}/evidence", headers=phase2.headers(Role.OFFICER)
        )
    ).json()
    assert officer["after"] == returned["after"] and officer["card_url"] == returned["card_url"]
    await completion(phase2, key="correction-round-two", round_=2)
    current = await view(phase2)
    assert current["can_verify"] and current["round"] == current["after_round"] == 2
    assert current["after"] != original["after"]
    assert current["verdict_label"] == "Awaiting citizen verification"
    stale = await verdict(phase2, True, round_=1, key="fresh-stale-request")
    assert stale.status_code == 409
    assert (await verdict(phase2, True, round_=2, key="round-two-verdict")).status_code == 200
    async with phase2.sessions() as session:
        records = (await session.scalars(select(Verification).order_by(Verification.round))).all()
        assert [(record.round, record.verdict) for record in records] == [(1, False), (2, True)]
        assert await session.scalar(select(func.count()).select_from(Allocation)) == 1
        photos = (
            await session.scalars(select(MediaAsset).where(MediaAsset.work_order_id == ORDER))
        ).all()
        assert sorted(photo.round for photo in photos) == [1, 2]
        audit = (
            await session.scalars(
                select(AuditEventRecord).where(
                    AuditEventRecord.entity_id == CLUSTER,
                    AuditEventRecord.action == "cluster.status_changed",
                )
            )
        ).all()
        rejected = next(event for event in audit if event.after.get("verdict") is False)
        assert rejected.before["round"] == 1 and rejected.after["round"] == 2


async def test_report_without_before_photo_remains_verifiable(phase2: Phase2) -> None:
    await ready(phase2, before=False)
    result = await view(phase2)
    assert result["before"] is None and result["after"] and result["can_verify"]
    assert phase2.media.cards[-1].before is None
    assert (await verdict(phase2, True)).status_code == 200


async def test_exact_concurrent_retries_record_one_negative_verdict(phase2: Phase2) -> None:
    await ready(phase2)
    responses = await asyncio.gather(*[verdict(phase2, False, key="same-key") for _ in range(4)])
    assert [response.status_code for response in responses] == [200] * 4
    assert len({response.text for response in responses}) == 1
    # The same saved response is replayed even after the negative verdict advanced the round.
    assert (await verdict(phase2, False, key="same-key")).json() == responses[0].json()
    assert (await verdict(phase2, True, key="same-key")).status_code == 409
    async with phase2.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Verification)) == 1
        assert (await session.get(WorkOrder, ORDER)).round == 2
        assert (
            await session.scalar(
                select(func.count())
                .select_from(IdempotencyKey)
                .where(IdempotencyKey.operation == "work_orders.verify")
            )
            == 1
        )


async def test_competing_verdicts_record_exactly_one_result(phase2: Phase2) -> None:
    await ready(phase2)
    responses = await asyncio.gather(
        *[verdict(phase2, index % 2 == 0, key=f"competing-{index}") for index in range(4)]
    )
    assert sorted(response.status_code for response in responses) == [200, 409, 409, 409]
    async with phase2.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Verification)) == 1
        assert await session.scalar(select(func.count()).select_from(Allocation)) == 1


async def test_stale_round_and_wrong_owner_write_nothing(phase2: Phase2) -> None:
    await ready(phase2)
    assert (await verdict(phase2, True, round_=2)).status_code == 409
    stranger = await add_user(phase2, "stranger-verifier", Role.CITIZEN)
    # Eligibility wins over a stale round. A citizen with no report in the
    # cluster gets 404, as the verification view does: nothing is revealed.
    assert (await verdict(phase2, True, round_=999, headers=stranger)).status_code == 404
    assert (
        await phase2.client.get(f"/api/v1/reports/{ANCHOR}/verification", headers=stranger)
    ).status_code == 404
    for role in [Role.OFFICER, Role.DEPARTMENT, Role.PANCHAYAT, Role.SUPER_ADMIN]:
        assert (await verdict(phase2, True, headers=phase2.headers(role))).status_code == 403
    async with phase2.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Verification)) == 0
        assert (
            await session.scalar(
                select(func.count())
                .select_from(IdempotencyKey)
                .where(IdempotencyKey.operation == "work_orders.verify")
            )
            == 0
        )
        assert (await session.get(Cluster, CLUSTER)).status == "awaiting_verification"


async def test_member_reporter_can_review_but_only_anchor_reporter_can_verify(
    phase2: Phase2,
) -> None:
    await ready(phase2)
    headers = await add_user(phase2, "member-reporter", Role.CITIZEN)
    async with phase2.sessions.begin() as session:
        from app.modules.users.models import User

        user = await session.scalar(select(User).where(User.firebase_uid == "member-reporter"))
        member = new_report("Another report of the same pump")
        member.reporter_id = user.id
        member.status = "verified"
        member.cluster_id = CLUSTER
        session.add(member)
        await session.flush()
        report_id = member.id
    review = await view(phase2, report_id, headers)
    assert review["after"] and not review["can_verify"]
    assert "original report" in review["blocked_reason"]
    assert (await verdict(phase2, True, headers=headers)).status_code == 403


async def test_completion_from_before_a_return_is_refused(phase2: Phase2) -> None:
    await ready(phase2)
    assert (await verdict(phase2, False, key="return-before-stale")).status_code == 200
    # A second tab still showing round 1 submits its unused photos.
    photo = await completed_media(phase2, Role.OFFICER)
    stale = await phase2.client.post(
        f"/api/v1/work-orders/{ORDER}/complete",
        json={"media_ids": [photo], "expected_round": 1},
        headers=phase2.headers(Role.OFFICER, **{"Idempotency-Key": "stale-tab"}),
    )
    assert stale.status_code == 409, stale.text
    async with phase2.sessions() as session:
        assert (await session.get(MediaAsset, UUID(photo))).work_order_id is None
        assert (await session.get(Cluster, CLUSTER)).status == "in_progress"
    # The current round's submission still goes through.
    await completion(phase2, key="current-tab", round_=2)
    current = await view(phase2)
    assert current["can_verify"] and current["after_round"] == 2


async def test_verification_is_unavailable_before_completion(phase2: Phase2) -> None:
    for report_id in [ANCHOR, seed_id("report/reported"), seed_id("report/prioritised"), uuid4()]:
        response = await phase2.client.get(
            f"/api/v1/reports/{report_id}/verification", headers=phase2.headers()
        )
        assert response.status_code == 404
    assert (await verdict(phase2, True)).status_code == 409


async def test_officer_who_moves_department_loses_old_evidence_and_assignment_reads(
    phase2: Phase2,
) -> None:
    from app.modules.users.models import User
    from app.seeds.data import user_id

    await ready(phase2)
    elsewhere = await other_department(phase2)
    async with phase2.sessions.begin() as session:
        await session.execute(
            update(User).where(User.id == user_id(Role.OFFICER)).values(department_id=elsewhere)
        )
    headers = phase2.headers(Role.OFFICER)
    assert (
        await phase2.client.get(f"/api/v1/work-orders/{ORDER}/evidence", headers=headers)
    ).status_code == 404
    assert (await phase2.client.get("/api/v1/work-orders?mine=true", headers=headers)).json() == {
        "items": []
    }


async def test_failed_commit_rolls_back_verdict_round_audit_and_retry_key(phase2: Phase2) -> None:
    await ready(phase2)

    async def fail_commit():
        async with phase2.sessions() as session:
            try:
                yield session
                raise RuntimeError("Simulated commit failure")
            finally:
                await session.rollback()

    phase2.app.dependency_overrides[get_db] = fail_commit
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=phase2.app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"/api/v1/work-orders/{ORDER}/verify",
            json={"verdict": False, "expected_round": 1},
            headers=phase2.headers(**{"Idempotency-Key": "rollback-verdict"}),
        )
    assert response.status_code == 500
    async with phase2.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Verification)) == 0
        assert (await session.get(WorkOrder, ORDER)).round == 1
        assert (await session.get(Cluster, CLUSTER)).status == "awaiting_verification"
        assert (
            await session.scalar(
                select(func.count())
                .select_from(IdempotencyKey)
                .where(IdempotencyKey.operation == "work_orders.verify")
            )
            == 0
        )
        audits = (
            await session.scalars(
                select(AuditEventRecord).where(AuditEventRecord.entity_id == CLUSTER)
            )
        ).all()
        assert all("verdict" not in (event.after or {}) for event in audits)


async def test_full_report_to_correction_to_citizen_verified_journey(phase2: Phase2) -> None:
    photo = await completed_media(phase2)
    response = await phase2.client.post(
        "/api/v1/reports",
        json=report_body(media_ids=[photo]),
        headers=phase2.headers(**{"Idempotency-Key": "journey-report"}),
    )
    assert response.status_code == 201, response.text
    report_id = response.json()["id"]
    base = f"/api/v1/reports/{report_id}"
    assert (
        await phase2.client.post(
            base + "/validate", json={"decision": "verify"}, headers=phase2.headers(Role.PANCHAYAT)
        )
    ).status_code == 200
    assert (
        await phase2.client.post(
            base + "/cluster", json={"new": True}, headers=phase2.headers(Role.PANCHAYAT)
        )
    ).status_code == 200
    report = (await phase2.client.get(base, headers=phase2.headers())).json()
    funded = await phase2.client.post(
        f"/api/v1/clusters/{report['cluster_id']}/fund",
        json={"officer_id": str(seed_id("user/officer")), "amount_paise": 250000},
        headers=phase2.headers(Role.DEPARTMENT, **{"Idempotency-Key": "journey-fund"}),
    )
    assert funded.status_code == 201, funded.text
    order = funded.json()["work_order_id"]
    assert (
        await phase2.client.patch(
            f"/api/v1/work-orders/{order}",
            json={"notes": "Repair started"},
            headers=phase2.headers(Role.OFFICER),
        )
    ).status_code == 200
    await completion(phase2, order, "journey-complete-one")
    first = await view(phase2, report_id)
    assert first["can_verify"] and first["card_url"]
    assert (await verdict(phase2, False, order=order, key="journey-return")).status_code == 200
    returned = await view(phase2, report_id)
    assert not returned["can_verify"] and returned["after"] == first["after"]
    await completion(phase2, order, "journey-complete-two", round_=2)
    second = await view(phase2, report_id)
    assert second["round"] == second["after_round"] == 2 and second["after"] != first["after"]
    assert (
        await verdict(phase2, True, order=order, round_=2, key="journey-confirm")
    ).status_code == 200
    final = await view(phase2, report_id)
    detail = (await phase2.client.get(base, headers=phase2.headers())).json()
    assert final["status"] == detail["status"] == "citizen_verified"
    assert phase2.media.cards[-1].verdict_label == "Citizen verified"
    async with phase2.sessions() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(Allocation)
                .where(Allocation.work_order_id == UUID(order))
            )
            == 1
        )
        records = (
            await session.scalars(
                select(Verification)
                .where(Verification.work_order_id == UUID(order))
                .order_by(Verification.round)
            )
        ).all()
        assert [(row.round, row.verdict) for row in records] == [(1, False), (2, True)]
