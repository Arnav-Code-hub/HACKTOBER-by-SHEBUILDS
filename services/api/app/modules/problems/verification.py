"""Citizen evidence reads and atomic verdicts against the reviewed repair round."""

from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, PermissionDeniedError
from app.core.idempotency import RequestIdentity, StoredResponse, request_hash
from app.core.roles import Role
from app.core.security import Principal
from app.integrations.cloudinary import MediaProvider
from app.modules.notifications.service import publish_case_update
from app.modules.problems.models import Cluster, Report, Support, WorkOrder
from app.modules.problems.schemas import StatusAck, VerificationRead, VerifyWorkOrder
from app.modules.problems.work_orders import evidence_for_order
from app.persistence.idempotency import SqlIdempotencyStore
from app.persistence.lifecycle import SqlTransitionStore
from app.shared.enums import ProblemStatus as Status


def _citizen(principal: Principal) -> None:
    if principal.role != Role.CITIZEN or principal.district_id is None:
        raise PermissionDeniedError("Only citizens can review and verify their repairs.")


async def verification_view(
    session: AsyncSession, principal: Principal, report_id: UUID, provider: MediaProvider
) -> VerificationRead:
    _citizen(principal)
    report = await session.scalar(
        select(Report).where(
            Report.id == report_id,
            Report.reporter_id == principal.user_id,
            Report.district_id == principal.district_id,
        )
    )
    if report is None:
        raise NotFoundError("Report not found.")
    row = (
        await session.execute(
            select(WorkOrder, Cluster, Report)
            .join(Cluster, WorkOrder.cluster_id == Cluster.id)
            .join(Report, Cluster.anchor_report_id == Report.id)
            .where(Cluster.id == report.cluster_id)
        )
    ).one_or_none()
    if row is None:
        raise NotFoundError("Verification opens once the repair work has been submitted.")
    work, cluster, anchor = row.WorkOrder, row.Cluster, row.Report
    # Current state/round come from one SELECT; a verdict submitted after they
    # change is refused by the row-locked expected_round check, not trusted UI.
    details = await evidence_for_order(session, work, cluster, anchor, provider)
    if details.after is None:
        raise NotFoundError("Verification opens once the repair work has been submitted.")
    can_verify = (
        anchor.reporter_id == principal.user_id and cluster.status == Status.AWAITING_VERIFICATION
    )
    blocked = None
    if anchor.reporter_id != principal.user_id:
        blocked = "Only the citizen who filed the cluster's original report can verify this repair."
    elif cluster.status == Status.CITIZEN_VERIFIED:
        blocked = "You have already confirmed this repair."
    elif cluster.status != Status.AWAITING_VERIFICATION:
        blocked = (
            "The previous attempt was returned for correction. Wait for new completion evidence."
        )
    return VerificationRead(
        **details.model_dump(),
        work_order_id=work.id,
        title=anchor.title,
        category=anchor.category,
        round=work.round,
        can_verify=can_verify,
        blocked_reason=blocked,
    )


async def verify_work_order(
    session: AsyncSession,
    principal: Principal,
    work_order_id: UUID,
    body: VerifyWorkOrder,
    key: str,
) -> StoredResponse:
    _citizen(principal)
    identity = RequestIdentity(
        principal.user_id,
        "work_orders.verify",
        key,
        request_hash({"work_order_id": str(work_order_id), **body.model_dump(mode="json")}),
    )

    async def action() -> StoredResponse:
        work = await session.get(WorkOrder, work_order_id)
        # A citizen with no report in this cluster learns nothing about it,
        # matching the verification view. A member reporter can see the case,
        # so the transition's original-reporter check refuses them with 403.
        if work is None or not await session.scalar(
            select(
                exists().where(
                    Report.cluster_id == work.cluster_id,
                    Report.reporter_id == principal.user_id,
                )
            )
        ):
            raise NotFoundError("Work order not found.")
        # The shared transition locks cluster then work order, checks original
        # reporter eligibility before state/round, records this round's verdict,
        # advances only on rejection, and audits in this caller transaction.
        snapshot = await SqlTransitionStore("cluster").transition(
            session,
            work.cluster_id,
            Status.AWAITING_VERIFICATION,
            Status.CITIZEN_VERIFIED if body.verdict else Status.IN_PROGRESS,
            actor=principal,
            reason=None,
            expected_round=body.expected_round,
            comment=body.comment,
        )
        recipients = await session.scalars(
            select(Report.reporter_id).where(Report.cluster_id == work.cluster_id).distinct()
        )
        supporters = await session.scalars(
            select(Support.user_id).where(Support.cluster_id == work.cluster_id).distinct()
        )
        await publish_case_update(
            session,
            [*recipients.all(), *supporters.all()],
            # Per round and verdict, so a returned round never collides with
            # "work started" or with the next round's verdict.
            event_key=(
                f"cluster.verdict.round.{body.expected_round}."
                f"{'confirmed' if body.verdict else 'returned'}"
            ),
            title=(
                "Repair confirmed by a citizen" if body.verdict else "Repair needs another attempt"
            ),
            body=(
                "A citizen confirmed the completed repair."
                if body.verdict
                else "A citizen requested more work. New completion evidence will be shared."
            ),
            resource_type="cluster",
            resource_id=work.cluster_id,
        )
        return StoredResponse(
            200, StatusAck(id=work.id, status=snapshot.status).model_dump(mode="json")
        )

    return await SqlIdempotencyStore().execute(session, identity, action)
