"""Funding, government work orders and their evidence.

A cluster is funded once: the allocation, its work order, the status change and
the audit entry commit together. The cluster stays the one execution status;
work orders carry the assignment, round and notes. Student projects are a
separate module and never create or approve a work order.
"""

from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import evidence
from app.core.audit import AuditEvent
from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from app.core.idempotency import RequestIdentity, StoredResponse, request_hash
from app.core.roles import Role
from app.core.scope import require_assignment, require_district
from app.core.security import Principal
from app.integrations.cloudinary import MediaProvider
from app.modules.files.schemas import EvidencePhoto
from app.modules.files.service import (
    attach_completion_media,
    completion_photos_by_round,
    first_report_photo,
)
from app.modules.funding.service import allocated_paise, record_allocation
from app.modules.notifications.service import publish_case_update
from app.modules.problems.models import Cluster, Report, Support, Verification, WorkOrder
from app.modules.problems.schemas import (
    CompleteWorkOrder,
    EvidencePhotoRead,
    EvidenceRead,
    FundCluster,
    FundResult,
    StatusAck,
    WorkOrderList,
    WorkOrderRead,
    WorkOrderUpdate,
)
from app.modules.users.service import is_assignable_officer
from app.persistence.audit import SqlAuditWriter
from app.persistence.idempotency import SqlIdempotencyStore
from app.persistence.lifecycle import SqlTransitionStore
from app.shared.enums import ProblemStatus as Status


async def _notify_case(
    session: AsyncSession,
    cluster: Cluster,
    *,
    event_key: str,
    title: str,
    body: str,
) -> None:
    reporters = await session.scalars(
        select(Report.reporter_id).where(Report.cluster_id == cluster.id).distinct()
    )
    supporters = await session.scalars(
        select(Support.user_id).where(Support.cluster_id == cluster.id).distinct()
    )
    await publish_case_update(
        session,
        [*reporters.all(), *supporters.all()],
        event_key=event_key,
        title=title,
        body=body,
        resource_type="cluster",
        resource_id=cluster.id,
    )


def _orders() -> Select[tuple[WorkOrder, Cluster, Report]]:
    return (
        select(WorkOrder, Cluster, Report)
        .join(Cluster, WorkOrder.cluster_id == Cluster.id)
        .join(Report, Cluster.anchor_report_id == Report.id)
    )


async def _locked(session: AsyncSession, work_order_id: UUID) -> tuple[WorkOrder, Cluster]:
    """Lock in the shared order — cluster, then work order — before writing."""
    work = await session.get(WorkOrder, work_order_id)
    if work is None:
        raise NotFoundError("Work order not found.")
    cluster = await session.scalar(
        select(Cluster)
        .where(Cluster.id == work.cluster_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    work = await session.scalar(
        select(WorkOrder)
        .where(WorkOrder.id == work_order_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    assert cluster is not None and work is not None  # foreign key, same transaction
    return work, cluster


def _officer(principal: Principal) -> None:
    if principal.role != Role.OFFICER:
        raise PermissionDeniedError("Only the assigned officer can update this work.")


async def fund_cluster(
    session: AsyncSession,
    principal: Principal,
    cluster_id: UUID,
    body: FundCluster,
    key: str,
) -> StoredResponse:
    if (
        principal.role != Role.DEPARTMENT
        or principal.department_id is None
        or principal.district_id is None
    ):
        raise PermissionDeniedError("Only the responsible department can fund a cluster.")
    department_id = principal.department_id
    identity = RequestIdentity(
        principal.user_id,
        "clusters.fund",
        key,
        # The cluster is part of the request: one key cannot fund two clusters.
        request_hash({**body.model_dump(mode="json"), "cluster_id": str(cluster_id)}),
    )

    async def action() -> StoredResponse:
        cluster = await session.get(Cluster, cluster_id)
        if cluster is None:
            raise NotFoundError("Cluster not found.")
        require_district(principal, cluster.district_id)
        if not await is_assignable_officer(
            session, body.officer_id, cluster.district_id, department_id
        ):
            raise ValidationError("Assign an active officer from your own department and district.")
        # Locks the cluster, checks this department is responsible for the
        # category, and refuses (409) unless it is still prioritised.
        await SqlTransitionStore("cluster").transition(
            session, cluster.id, Status.PRIORITISED, Status.FUNDED, actor=principal, reason=None
        )
        work = WorkOrder(
            cluster_id=cluster.id,
            department_id=department_id,
            district_id=cluster.district_id,
            officer_id=body.officer_id,
            instructions=body.notes or "",
            is_demo=principal.is_demo,
        )
        session.add(work)
        await session.flush()
        allocation_id = await record_allocation(
            session,
            cluster_id=cluster.id,
            work_order_id=work.id,
            amount_paise=body.amount_paise,
            allocated_by=principal.user_id,
            is_demo=principal.is_demo,
        )
        await SqlAuditWriter().log_event(
            session,
            AuditEvent(
                principal.user_id,
                "cluster.funded",
                "cluster",
                cluster.id,
                cluster.district_id,
                after={
                    "allocation_id": str(allocation_id),
                    "work_order_id": str(work.id),
                    "amount_paise": body.amount_paise,
                    "officer_id": str(body.officer_id),
                },
            ),
        )
        await _notify_case(
            session,
            cluster,
            event_key="cluster.status.funded",
            title="A community case was funded",
            body="A department allocated funding and assigned repair work.",
        )
        result = FundResult(allocation_id=allocation_id, work_order_id=work.id)
        return StoredResponse(201, result.model_dump(mode="json"))

    return await SqlIdempotencyStore().execute(session, identity, action)


async def my_work_orders(session: AsyncSession, principal: Principal) -> WorkOrderList:
    _officer(principal)
    rows = (
        await session.execute(
            _orders()
            .where(
                WorkOrder.officer_id == principal.user_id,
                WorkOrder.district_id == principal.district_id,
                WorkOrder.department_id == principal.department_id,
            )
            .order_by(WorkOrder.assigned_at.desc(), WorkOrder.id)
        )
    ).all()
    amounts = await allocated_paise(session, [row.WorkOrder.id for row in rows])
    return WorkOrderList(
        items=[
            WorkOrderRead(
                id=row.WorkOrder.id,
                cluster_id=row.Cluster.id,
                report_code=row.Report.code,
                title=row.Report.title,
                status=Status(row.Cluster.status),
                round=row.WorkOrder.round,
                location_label=row.Report.location_label or None,
                instructions=row.WorkOrder.instructions or None,
                notes=row.WorkOrder.notes or None,
                allocated_paise=amounts.get(row.WorkOrder.id, 0),
                assigned_at=row.WorkOrder.assigned_at,
            )
            for row in rows
        ]
    )


async def update_work_order(
    session: AsyncSession, principal: Principal, work_order_id: UUID, body: WorkOrderUpdate
) -> StatusAck:
    _officer(principal)
    work = await session.get(WorkOrder, work_order_id)
    if work is None:
        raise NotFoundError("Work order not found.")
    require_assignment(principal, work.district_id, work.department_id, work.officer_id)
    cluster = await session.get(Cluster, work.cluster_id)
    assert cluster is not None
    started = cluster.status == Status.FUNDED
    if started:
        # The first progress note starts the work.
        snapshot = await SqlTransitionStore("cluster").transition(
            session, cluster.id, Status.FUNDED, Status.IN_PROGRESS, actor=principal, reason=None
        )
        status = snapshot.status
    else:
        work, cluster = await _locked(session, work_order_id)
        if cluster.status != Status.IN_PROGRESS:
            raise ConflictError("Progress notes can be added only while the work is open.")
        status = Status.IN_PROGRESS
    before = work.notes
    work.notes = body.notes
    await SqlAuditWriter().log_event(
        session,
        AuditEvent(
            principal.user_id,
            "work_order.updated",
            "work_order",
            work.id,
            work.district_id,
            before={"notes": before},
            after={"notes": body.notes},
        ),
    )
    if started:
        await _notify_case(
            session,
            cluster,
            event_key="cluster.status.in_progress",
            title="Repair work has started",
            body="The assigned officer has started work on this community case.",
        )
    return StatusAck(id=work.id, status=status)


async def complete_work_order(
    session: AsyncSession,
    principal: Principal,
    work_order_id: UUID,
    body: CompleteWorkOrder,
    key: str,
) -> StoredResponse:
    _officer(principal)
    identity = RequestIdentity(
        principal.user_id,
        "work_orders.complete",
        key,
        request_hash(
            {
                "work_order_id": str(work_order_id),
                "media_ids": [str(media_id) for media_id in body.media_ids],
                "expected_round": body.expected_round,
            }
        ),
    )

    async def action() -> StoredResponse:
        work, cluster = await _locked(session, work_order_id)
        require_assignment(principal, work.district_id, work.department_id, work.officer_id)
        if cluster.status != Status.IN_PROGRESS:
            raise ConflictError("Completion evidence can be submitted only while work is open.")
        if work.round != body.expected_round:
            raise ConflictError(
                "The citizen returned this work since you opened it. Reload and submit "
                "new photos for the current round."
            )
        # Photos first, stamped with the current round; the transition then
        # requires a completion photo for exactly that round.
        await attach_completion_media(
            session, body.media_ids, principal.user_id, work.id, work.round
        )
        snapshot = await SqlTransitionStore("cluster").transition(
            session,
            cluster.id,
            Status.IN_PROGRESS,
            Status.AWAITING_VERIFICATION,
            actor=principal,
            reason=None,
        )
        await _notify_case(
            session,
            cluster,
            # One update per round: a correction round must notify again.
            event_key=f"cluster.status.{snapshot.status}.round.{work.round}",
            title="Repair work is ready for review",
            body="Completion evidence was submitted. Please review the repair in JanMaang.",
        )
        return StoredResponse(
            200, StatusAck(id=work.id, status=snapshot.status).model_dump(mode="json")
        )

    return await SqlIdempotencyStore().execute(session, identity, action)


def _require_evidence_access(principal: Principal, work: WorkOrder, anchor: Report) -> None:
    """Reporter, assigned officer, responsible department, district oversight."""
    if principal.role == Role.SUPER_ADMIN:
        return
    require_district(principal, work.district_id)
    if principal.role == Role.CITIZEN:
        if anchor.reporter_id != principal.user_id:
            raise NotFoundError("Work order not found.")
        return
    if (
        principal.role in {Role.PANCHAYAT, Role.GOV_ADMIN}
        or (principal.role == Role.DEPARTMENT and principal.department_id == work.department_id)
        or (
            principal.role == Role.OFFICER
            and principal.user_id == work.officer_id
            and principal.department_id == work.department_id
        )
    ):
        return
    raise NotFoundError("Work order not found.")


def _photo(photo: EvidencePhoto | None) -> EvidencePhotoRead | None:
    return (
        None if photo is None else EvidencePhotoRead(url=photo.url, uploaded_at=photo.uploaded_at)
    )


async def work_order_evidence(
    session: AsyncSession,
    principal: Principal,
    work_order_id: UUID,
    provider: MediaProvider,
) -> EvidenceRead:
    row = (await session.execute(_orders().where(WorkOrder.id == work_order_id))).one_or_none()
    if row is None:
        raise NotFoundError("Work order not found.")
    work, cluster, anchor = row.WorkOrder, row.Cluster, row.Report
    _require_evidence_access(principal, work, anchor)
    return await evidence_for_order(session, work, cluster, anchor, provider)


async def evidence_for_order(
    session: AsyncSession,
    work: WorkOrder,
    cluster: Cluster,
    anchor: Report,
    provider: MediaProvider,
) -> EvidenceRead:
    """One composition for authorized work-order and citizen verification views.

    The caller must have established access before invoking this module helper.
    """
    before = await first_report_photo(session, anchor.id, provider)
    rounds = await completion_photos_by_round(session, work.id, provider)
    # The one selection rule shared with the verification view and the card.
    selection = evidence.select(
        before=evidence.EvidenceAsset(str(before.id), before.public_id) if before else None,
        status=Status(cluster.status),
        round_=work.round,
        completions={
            number: evidence.EvidenceAsset(str(photo.id), photo.public_id)
            for number, photo in rounds.items()
        },
    )
    after = rounds[selection.after_round] if selection.after_round is not None else None
    card_url = None
    if after is not None and selection.after_round is not None and selection.verdict_label:
        card_url = provider.evidence_card(
            evidence.EvidenceCard(
                report_code=anchor.code,
                before=evidence.CardPhoto(before.public_id, before.version, before.uploaded_at)
                if before
                else None,
                after=evidence.CardPhoto(after.public_id, after.version, after.uploaded_at),
                after_round=selection.after_round,
                verdict_label=selection.verdict_label,
            )
        )
    returned_comment = None
    if cluster.status == Status.IN_PROGRESS and selection.after_round is not None:
        # The round on show was returned; its verdict carries the reason.
        returned_comment = await session.scalar(
            select(Verification.comment).where(
                Verification.work_order_id == work.id,
                Verification.round == selection.after_round,
                Verification.verdict.is_(False),
            )
        )
    return EvidenceRead(
        report_code=anchor.code,
        status=Status(cluster.status),
        before=_photo(before),
        after=_photo(after),
        after_round=selection.after_round,
        card_url=card_url,
        verdict_label=selection.verdict_label,
        returned_comment=returned_comment,
    )
