import asyncio
from collections.abc import AsyncIterator
from dataclasses import replace

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.audit import AuditEvent
from app.core.config import Settings
from app.core.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.core.idempotency import RequestIdentity, StoredResponse, request_hash
from app.core.roles import Role
from app.modules.audit.models import AuditEventRecord
from app.modules.auth.models import IdempotencyKey
from app.modules.funding.models import Allocation
from app.modules.problems.models import Cluster, Report, Verification, WorkOrder
from app.persistence.audit import SqlAuditWriter
from app.persistence.idempotency import SqlIdempotencyStore
from app.persistence.lifecycle import SqlTransitionStore, report_status
from app.seeds.data import SEED_AT, seed_id, user_id
from app.seeds.loader import reset_demo, seed
from app.shared.enums import ProblemStatus as Status
from tests.integration.helpers import completion_photo, demo_principal, new_report

pytestmark = pytest.mark.integration


@pytest.fixture
async def committed_seed(db_engine: AsyncEngine, migrated_database: str) -> AsyncIterator[None]:
    # Only the explicitly designated isolated test database is reset.
    url = make_url(migrated_database)
    settings = Settings(
        _env_file=None,
        database_url=migrated_database,
        environment="staging",
        seed_reset_allowed=True,
        seed_reset_targets=[f"{url.username}@{url.host}:{url.port or 5432}/{url.database}"],
    )
    sessions = async_sessionmaker(db_engine)
    async with sessions.begin() as session:
        await reset_demo(session, settings)
        await seed(session)
    yield
    async with sessions.begin() as session:
        await reset_demo(session, settings)


async def test_idempotency_rollback_removes_reservation_business_write_and_audit(
    db_session: AsyncSession,
) -> None:
    await seed(db_session)
    identity = RequestIdentity(user_id(Role.CITIZEN), "reports.create", "failure", request_hash({}))

    async def action() -> StoredResponse:
        report = new_report("Rolled back report")
        db_session.add(report)
        await db_session.flush()
        await SqlAuditWriter().log_event(
            db_session,
            AuditEvent(
                user_id(Role.CITIZEN),
                "probe.created",
                "report",
                report.id,
                seed_id("district/yadgir"),
            ),
        )
        raise ValueError("simulated action failure")

    with pytest.raises(ValueError, match="simulated"):
        await SqlIdempotencyStore().execute(db_session, identity, action)
    # Caller can catch the error and commit other work safely.
    await db_session.commit()
    assert await db_session.scalar(select(func.count()).select_from(IdempotencyKey)) == 0
    assert await db_session.scalar(select(func.count()).select_from(Report)) == 3
    assert await db_session.scalar(select(func.count()).select_from(AuditEventRecord)) == 1


@pytest.mark.parametrize("different_payload", [False, True])
async def test_concurrent_idempotency_waits_and_runs_business_action_once(
    db_engine: AsyncEngine,
    committed_seed: None,
    different_payload: bool,
) -> None:
    entered, release = asyncio.Event(), asyncio.Event()
    sessions = async_sessionmaker(db_engine, expire_on_commit=False)
    calls = 0
    identity = RequestIdentity(
        user_id(Role.CITIZEN), "reports.create", "same-key", request_hash({"x": 1})
    )

    async def request(request_identity: RequestIdentity) -> StoredResponse:
        async with sessions.begin() as session:

            async def action() -> StoredResponse:
                nonlocal calls
                calls += 1
                record = new_report("Concurrent report")
                session.add(record)
                await session.flush()
                await SqlAuditWriter().log_event(
                    session,
                    AuditEvent(
                        user_id(Role.CITIZEN),
                        "probe.created",
                        "report",
                        record.id,
                        seed_id("district/yadgir"),
                    ),
                )
                entered.set()
                await asyncio.wait_for(release.wait(), 10)
                return StoredResponse(201, {"id": str(record.id), "code": record.code})

            return await SqlIdempotencyStore().execute(session, request_identity, action)

    first = asyncio.create_task(request(identity))
    await asyncio.wait_for(entered.wait(), 10)
    second = asyncio.create_task(
        request(
            replace(identity, request_hash=request_hash({"x": 2}))
            if different_payload
            else identity
        )
    )
    try:
        # Observe actual PostgreSQL index-lock contention before releasing the
        # first writer; this test cannot accidentally pass with sequential calls.
        async with db_engine.connect() as connection:
            for _ in range(100):
                await connection.execute(text("SELECT pg_stat_clear_snapshot()"))
                blocked = await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                        "AND wait_event_type='Lock' AND query ILIKE '%idempotency_keys%'"
                    )
                )
                if blocked:
                    break
                await asyncio.sleep(0.02)
            assert blocked
    finally:
        release.set()
    results = await asyncio.wait_for(asyncio.gather(first, second, return_exceptions=True), 15)
    assert isinstance(results[0], StoredResponse)
    if different_payload:
        assert isinstance(results[1], ConflictError)
    else:
        assert results[0] == results[1]
    assert calls == 1
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(IdempotencyKey)) == 1
        assert await session.scalar(select(func.count()).select_from(Report)) == 4
        assert await session.scalar(select(func.count()).select_from(AuditEventRecord)) == 2


async def test_status_timestamp_audit_and_rollback_are_one_transaction(
    db_session: AsyncSession,
) -> None:
    await seed(db_session)
    store = SqlTransitionStore()
    actor = demo_principal(Role.PANCHAYAT)
    async with db_session.begin_nested() as transaction:
        snapshot = await store.transition(
            db_session,
            seed_id("report/reported"),
            Status.REPORTED,
            Status.VERIFIED,
            actor=actor,
            reason="Checked locally",
        )
        assert snapshot.status_changed_at > SEED_AT
        assert (await report_status(db_session, seed_id("report/reported"))) == snapshot
        event = (
            await db_session.scalars(
                select(AuditEventRecord).where(AuditEventRecord.action == "report.status_changed")
            )
        ).one()
        assert event.district_id == actor.district_id
        assert event.actor_role == Role.PANCHAYAT
        assert event.after["status"] == "verified"
        await transaction.rollback()
    assert (await report_status(db_session, seed_id("report/reported"))).status == Status.REPORTED
    assert await db_session.scalar(select(func.count()).select_from(AuditEventRecord)) == 1


async def test_wrong_state_role_and_scope_write_nothing(db_session: AsyncSession) -> None:
    await seed(db_session)
    store, actor = SqlTransitionStore(), demo_principal(Role.PANCHAYAT)
    with pytest.raises(ConflictError):
        await store.transition(
            db_session,
            seed_id("report/prioritised"),
            Status.REPORTED,
            Status.VERIFIED,
            actor=actor,
            reason=None,
        )
    with pytest.raises(NotFoundError):
        await store.transition(
            db_session,
            seed_id("report/reported"),
            Status.REPORTED,
            Status.VERIFIED,
            actor=replace(actor, district_id=seed_id("district/boundary")),
            reason=None,
        )
    with pytest.raises(PermissionDeniedError):
        await store.transition(
            db_session,
            seed_id("report/reported"),
            Status.REPORTED,
            Status.VERIFIED,
            actor=demo_principal(Role.CITIZEN),
            reason=None,
        )
    assert await db_session.scalar(select(func.count()).select_from(AuditEventRecord)) == 1


async def test_clustering_keeps_report_intake_status_and_uses_cluster_status(
    db_session: AsyncSession,
) -> None:
    await seed(db_session)
    store, actor = SqlTransitionStore(), demo_principal(Role.PANCHAYAT)
    report_id = seed_id("report/reported")
    await store.transition(
        db_session, report_id, Status.REPORTED, Status.VERIFIED, actor=actor, reason=None
    )
    result = await store.transition(
        db_session, report_id, Status.VERIFIED, Status.PRIORITISED, actor=actor, reason=None
    )
    assert result.status == Status.PRIORITISED
    report = await db_session.get(Report, report_id)
    assert report.status == Status.VERIFIED
    assert report.cluster_id is not None
    assert await report_status(db_session, report_id) == result
    with pytest.raises(ConflictError):
        await store.transition(
            db_session, report_id, Status.VERIFIED, Status.PRIORITISED, actor=actor, reason=None
        )


async def test_execution_status_and_negative_round_preserve_allocation(
    db_session: AsyncSession,
) -> None:
    await seed(db_session)
    store, cluster_id = SqlTransitionStore("cluster"), seed_id("cluster/in_progress")
    db_session.add(completion_photo(seed_id("work-order"), 1))
    snapshot = await store.transition(
        db_session,
        cluster_id,
        Status.IN_PROGRESS,
        Status.AWAITING_VERIFICATION,
        actor=demo_principal(Role.OFFICER),
        reason=None,
    )
    assert await report_status(db_session, seed_id("report/in_progress")) == snapshot
    with pytest.raises(ConflictError):
        await store.transition(
            db_session,
            cluster_id,
            Status.AWAITING_VERIFICATION,
            Status.CITIZEN_VERIFIED,
            actor=demo_principal(Role.CITIZEN),
            reason=None,
            expected_round=2,
        )
    with pytest.raises(PermissionDeniedError):
        await store.transition(
            db_session,
            cluster_id,
            Status.AWAITING_VERIFICATION,
            Status.CITIZEN_VERIFIED,
            actor=replace(demo_principal(Role.CITIZEN), user_id=user_id(Role.STUDENT)),
            reason=None,
            expected_round=1,
        )
    await store.transition(
        db_session,
        cluster_id,
        Status.AWAITING_VERIFICATION,
        Status.IN_PROGRESS,
        actor=demo_principal(Role.CITIZEN),
        reason="Still broken",
        expected_round=1,
        comment="  Dry again by evening.  ",
    )
    work = await db_session.get(WorkOrder, seed_id("work-order"))
    assert work.round == 2
    # The verdict is stored against the round the citizen reviewed.
    verdict = (
        await db_session.scalars(
            select(Verification).where(Verification.work_order_id == seed_id("work-order"))
        )
    ).one()
    assert (verdict.round, verdict.verdict) == (1, False)
    assert verdict.comment == "Dry again by evening."
    assert verdict.citizen_id == user_id(Role.CITIZEN)
    event = (
        await db_session.scalars(
            select(AuditEventRecord).where(
                AuditEventRecord.action == "cluster.status_changed",
                AuditEventRecord.reason == "Still broken",
            )
        )
    ).one()
    assert event.before["round"] == 1
    assert event.after["round"] == 2
    assert await db_session.scalar(select(func.count()).select_from(Allocation)) == 1
    assert (
        await report_status(db_session, seed_id("report/in_progress"))
    ).status == Status.IN_PROGRESS


async def test_competing_transitions_only_one_commits(
    db_engine: AsyncEngine, committed_seed: None
) -> None:
    sessions = async_sessionmaker(db_engine, expire_on_commit=False)

    async def request() -> object:
        async with sessions.begin() as session:
            return await SqlTransitionStore().transition(
                session,
                seed_id("report/reported"),
                Status.REPORTED,
                Status.VERIFIED,
                actor=demo_principal(Role.PANCHAYAT),
                reason=None,
            )

    results = await asyncio.wait_for(
        asyncio.gather(request(), request(), return_exceptions=True), 15
    )
    assert sum(isinstance(result, ConflictError) for result in results) == 1
    async with sessions() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(AuditEventRecord)
                .where(AuditEventRecord.action == "report.status_changed")
            )
            == 1
        )


async def test_completion_requires_a_photo_for_the_current_round(
    db_session: AsyncSession,
) -> None:
    await seed(db_session)
    store, cluster_id = SqlTransitionStore("cluster"), seed_id("cluster/in_progress")
    officer = demo_principal(Role.OFFICER)
    with pytest.raises(ValidationError):
        await store.transition(
            db_session,
            cluster_id,
            Status.IN_PROGRESS,
            Status.AWAITING_VERIFICATION,
            actor=officer,
            reason=None,
        )
    assert (await db_session.get(Cluster, cluster_id)).status == Status.IN_PROGRESS

    # A photo from another round does not count for the current one.
    db_session.add(completion_photo(seed_id("work-order"), 2))
    with pytest.raises(ValidationError):
        await store.transition(
            db_session,
            cluster_id,
            Status.IN_PROGRESS,
            Status.AWAITING_VERIFICATION,
            actor=officer,
            reason=None,
        )

    db_session.add(completion_photo(seed_id("work-order"), 1))
    snapshot = await store.transition(
        db_session,
        cluster_id,
        Status.IN_PROGRESS,
        Status.AWAITING_VERIFICATION,
        actor=officer,
        reason=None,
    )
    assert snapshot.status == Status.AWAITING_VERIFICATION


async def test_positive_verdict_is_recorded_once_for_its_round(
    db_session: AsyncSession,
) -> None:
    await seed(db_session)
    store, cluster_id = SqlTransitionStore("cluster"), seed_id("cluster/in_progress")
    db_session.add(completion_photo(seed_id("work-order"), 1))
    await store.transition(
        db_session,
        cluster_id,
        Status.IN_PROGRESS,
        Status.AWAITING_VERIFICATION,
        actor=demo_principal(Role.OFFICER),
        reason=None,
    )
    await store.transition(
        db_session,
        cluster_id,
        Status.AWAITING_VERIFICATION,
        Status.CITIZEN_VERIFIED,
        actor=demo_principal(Role.CITIZEN),
        reason=None,
        expected_round=1,
    )
    with pytest.raises(ConflictError):
        await store.transition(
            db_session,
            cluster_id,
            Status.AWAITING_VERIFICATION,
            Status.CITIZEN_VERIFIED,
            actor=demo_principal(Role.CITIZEN),
            reason=None,
            expected_round=1,
        )
    verdicts = (
        await db_session.scalars(
            select(Verification).where(Verification.work_order_id == seed_id("work-order"))
        )
    ).all()
    assert [(v.round, v.verdict, v.comment) for v in verdicts] == [(1, True, None)]


@pytest.mark.parametrize(
    ("status", "joinable"),
    [
        (Status.PRIORITISED, True),
        (Status.FUNDED, True),
        (Status.IN_PROGRESS, True),
        (Status.AWAITING_VERIFICATION, False),
        (Status.CITIZEN_VERIFIED, False),
    ],
)
async def test_report_joins_only_a_cluster_before_verification(
    db_session: AsyncSession, status: Status, joinable: bool
) -> None:
    await seed(db_session)
    cluster = await db_session.get(Cluster, seed_id("cluster/prioritised"))
    cluster.status = status
    report = new_report("Recurring handpump fault")
    report.category = cluster.category
    db_session.add(report)
    await db_session.flush()
    store, panchayat = SqlTransitionStore(), demo_principal(Role.PANCHAYAT)
    await store.transition(
        db_session, report.id, Status.REPORTED, Status.VERIFIED, actor=panchayat, reason=None
    )

    async def join() -> object:
        return await store.transition(
            db_session,
            report.id,
            Status.VERIFIED,
            Status.PRIORITISED,
            actor=panchayat,
            reason=None,
            cluster_id=cluster.id,
        )

    if joinable:
        await join()
        assert (await db_session.get(Report, report.id)).cluster_id == cluster.id
    else:
        with pytest.raises(ConflictError):
            await join()
        # Refused without side effects: the report stays unclustered and can
        # start a new cluster instead, so the recurrence stays visible.
        assert (await db_session.get(Report, report.id)).cluster_id is None
        new_cluster = await store.transition(
            db_session, report.id, Status.VERIFIED, Status.PRIORITISED, actor=panchayat, reason=None
        )
        assert new_cluster.status == Status.PRIORITISED
