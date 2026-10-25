"""Row-locked status changes, historical timestamps and audit in one transaction.

Endpoint services still validate their business inputs (media, funding amount,
distance, etc.) and persist related records in the same caller transaction.
Every writer locks the cluster before its work order to avoid lock inversion.
"""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditEvent
from app.core.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.core.lifecycle import (
    JOINABLE_CLUSTER_STATUSES,
    StatusSnapshot,
    effective_status,
    require_transition_permission,
    validate_transition,
)
from app.core.scope import require_assignment, require_district
from app.core.security import Principal
from app.modules.departments.models import DepartmentCategory
from app.modules.files.models import MediaAsset
from app.modules.problems.models import Cluster, Report, Verification, WorkOrder
from app.persistence.audit import SqlAuditWriter
from app.shared.enums import ProblemStatus as Status
from app.shared.geo import cluster_radius_m, distance_m


async def report_status(session: AsyncSession, report_id: UUID) -> StatusSnapshot:
    row = (
        await session.execute(
            select(
                Report.status,
                Report.status_changed_at,
                Cluster.status.label("cluster_status"),
                Cluster.status_changed_at.label("cluster_changed_at"),
            )
            .outerjoin(Cluster, Report.cluster_id == Cluster.id)
            .where(Report.id == report_id)
        )
    ).one_or_none()
    if row is None:
        raise NotFoundError("Report not found.")
    return effective_status(
        StatusSnapshot(Status(row.status), row.status_changed_at),
        StatusSnapshot(Status(row.cluster_status), row.cluster_changed_at)
        if row.cluster_status is not None
        else None,
    )


class SqlTransitionStore:
    def __init__(self, record_kind: Literal["report", "cluster"] = "report") -> None:
        self.record_kind = record_kind
        self.audit = SqlAuditWriter()

    async def transition(
        self,
        session: AsyncSession,
        record_id: UUID,
        from_: Status,
        to: Status,
        *,
        actor: Principal,
        reason: str | None,
        expected_round: int | None = None,
        cluster_id: UUID | None = None,
        comment: str | None = None,
    ) -> StatusSnapshot:
        require_transition_permission(from_, to, actor)
        async with session.begin_nested():
            if self.record_kind == "report":
                record = await session.scalar(
                    select(Report)
                    .where(Report.id == record_id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
                if record is None:
                    raise NotFoundError("Report not found.")
                validate_transition(from_, to, actor=actor, reason=reason)
                require_district(actor, record.district_id)
                if record.cluster_id is not None or record.status != from_:
                    raise ConflictError("The report is no longer in the required state.")
                if to == Status.PRIORITISED:
                    return await self._cluster(session, record, cluster_id, actor, reason)
                record.status = to
                record.status_changed_at = datetime.now(UTC)
                record.rejection_reason = (
                    reason.strip() if to == Status.REJECTED and reason else None
                )
                snapshot = StatusSnapshot(to, record.status_changed_at)
                await self._audit(
                    session, actor, "report", record.id, record.district_id, from_, snapshot, reason
                )
                return snapshot

            cluster = await session.scalar(
                select(Cluster)
                .where(Cluster.id == record_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if cluster is None:
                raise NotFoundError("Cluster not found.")
            work = await session.scalar(
                select(WorkOrder)
                .where(WorkOrder.cluster_id == cluster.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            require_district(actor, cluster.district_id)
            if from_ == Status.PRIORITISED and to == Status.FUNDED:
                responsible = await session.scalar(
                    select(DepartmentCategory.department_id).where(
                        DepartmentCategory.district_id == cluster.district_id,
                        DepartmentCategory.category == cluster.category,
                    )
                )
                if responsible is None or responsible != actor.department_id:
                    raise PermissionDeniedError(
                        "Your department is not responsible for this category."
                    )
            elif from_ == Status.AWAITING_VERIFICATION:
                reporter = await session.scalar(
                    select(Report.reporter_id).where(Report.id == cluster.anchor_report_id)
                )
                if reporter != actor.user_id:
                    raise PermissionDeniedError(
                        "Only the original reporter can verify this repair."
                    )
            else:
                if work is None:
                    raise ConflictError("The cluster has no assigned work order.")
                require_assignment(actor, work.district_id, work.department_id, work.officer_id)
            # Reporter eligibility is checked before revealing whether a round
            # is current, as specified by the public verification contract.
            validate_transition(
                from_,
                to,
                actor=actor,
                reason=reason,
                current_round=work.round if work else None,
                expected_round=expected_round,
            )
            if cluster.status != from_:
                raise ConflictError("The cluster is no longer in the required state.")
            if to == Status.AWAITING_VERIFICATION:
                await self._require_completion_evidence(session, work)
            before_round = work.round if work is not None else None
            if from_ == Status.AWAITING_VERIFICATION:
                await self._record_verdict(
                    session, cluster, work, actor, to == Status.CITIZEN_VERIFIED, comment
                )
            if from_ == Status.AWAITING_VERIFICATION and to == Status.IN_PROGRESS:
                if work is None:
                    raise ConflictError("The cluster has no assigned work order.")
                work.round += 1
            cluster.status = to
            cluster.status_changed_at = datetime.now(UTC)
            snapshot = StatusSnapshot(to, cluster.status_changed_at)
            await self._audit(
                session,
                actor,
                "cluster",
                cluster.id,
                cluster.district_id,
                from_,
                snapshot,
                reason,
                before_round=before_round,
                after_round=work.round if work is not None else None,
            )
            return snapshot

    async def _cluster(
        self,
        session: AsyncSession,
        report: Report,
        cluster_id: UUID | None,
        actor: Principal,
        reason: str | None,
    ) -> StatusSnapshot:
        cluster: Cluster | None
        if cluster_id is None:
            cluster = Cluster(
                district_id=report.district_id,
                category=report.category,
                anchor_report_id=report.id,
                status=Status.PRIORITISED,
                status_changed_at=datetime.now(UTC),
                is_demo=report.is_demo,
            )
            session.add(cluster)
            await session.flush()
        else:
            cluster = await session.scalar(
                select(Cluster)
                .where(
                    Cluster.id == cluster_id,
                    Cluster.district_id == report.district_id,
                    Cluster.category == report.category,
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if cluster is None:
                raise NotFoundError("Matching cluster not found.")
            if Status(cluster.status) not in JOINABLE_CLUSTER_STATUSES:
                raise ConflictError(
                    "This cluster's repair is already awaiting or past citizen "
                    "verification. Start a new cluster for a recurring problem."
                )
            anchor = await session.get(Report, cluster.anchor_report_id)
            if anchor is None:
                raise NotFoundError("Cluster anchor not found.")
            if distance_m(
                report.latitude, report.longitude, anchor.latitude, anchor.longitude
            ) > cluster_radius_m(report.category):
                raise ValidationError("The report is outside this cluster's matching radius.")
        report.cluster_id = cluster.id
        snapshot = StatusSnapshot(Status(cluster.status), cluster.status_changed_at)
        await self._audit(
            session,
            actor,
            "report",
            report.id,
            report.district_id,
            Status.VERIFIED,
            snapshot,
            reason,
            cluster_id=cluster.id,
        )
        return snapshot

    async def _require_completion_evidence(
        self, session: AsyncSession, work: WorkOrder | None
    ) -> None:
        # Without a completion photo for the current round the evidence
        # endpoint and card have nothing to show, and the citizen cannot
        # verify. The endpoint attaches media first, in this transaction.
        if work is None:
            raise ConflictError("The cluster has no assigned work order.")
        photos = await session.scalar(
            select(func.count())
            .select_from(MediaAsset)
            .where(
                MediaAsset.work_order_id == work.id,
                MediaAsset.kind == "completion",
                MediaAsset.round == work.round,
            )
        )
        if not photos:
            raise ValidationError(
                f"Upload completion photos for round {work.round} before submitting."
            )

    async def _record_verdict(
        self,
        session: AsyncSession,
        cluster: Cluster,
        work: WorkOrder | None,
        actor: Principal,
        verdict: bool,
        comment: str | None,
    ) -> None:
        # Recorded here, against the round the citizen reviewed and before a
        # negative verdict advances it, so no caller can store the wrong round.
        if work is None:
            raise ConflictError("The cluster has no assigned work order.")
        text = comment.strip() if comment else None
        if text is not None and len(text) > 500:
            raise ValidationError("The comment can be at most 500 characters.")
        session.add(
            Verification(
                work_order_id=work.id,
                round=work.round,
                citizen_id=actor.user_id,
                verdict=verdict,
                comment=text or None,
                is_demo=cluster.is_demo,
            )
        )
        await session.flush()

    async def _audit(
        self,
        session: AsyncSession,
        actor: Principal,
        kind: str,
        entity_id: UUID,
        district_id: UUID,
        from_: Status,
        snapshot: StatusSnapshot,
        reason: str | None,
        *,
        before_round: int | None = None,
        after_round: int | None = None,
        cluster_id: UUID | None = None,
    ) -> None:
        await self.audit.log_event(
            session,
            AuditEvent(
                actor_id=actor.user_id,
                action=f"{kind}.status_changed",
                entity_type=kind,
                entity_id=entity_id,
                district_id=district_id,
                before={
                    "status": from_,
                    **({"round": before_round} if before_round is not None else {}),
                },
                after={
                    "status": snapshot.status,
                    "status_changed_at": snapshot.status_changed_at.isoformat()
                    if snapshot.status_changed_at
                    else None,
                    **({"round": after_round} if after_round is not None else {}),
                    **(
                        {"verdict": snapshot.status == Status.CITIZEN_VERIFIED}
                        if from_ == Status.AWAITING_VERIFICATION
                        else {}
                    ),
                    **({"cluster_id": str(cluster_id)} if cluster_id is not None else {}),
                },
                reason=reason,
            ),
        )
