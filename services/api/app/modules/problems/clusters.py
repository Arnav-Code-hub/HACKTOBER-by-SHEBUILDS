"""Panchayat confirmation, citizen support and official ranking inputs."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditEvent
from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError
from app.core.lifecycle import JOINABLE_CLUSTER_STATUSES
from app.core.roles import Role
from app.core.scope import require_district
from app.core.security import Principal
from app.modules.departments.service import department_categories, responsible_department
from app.modules.notifications.service import publish_case_update
from app.modules.problems.models import Cluster, Report, Support
from app.modules.problems.ranking import score_cluster
from app.modules.problems.repository import ClusterSnapshot, cluster_snapshots
from app.modules.problems.schemas import (
    AssignCluster,
    ClusterSuggestion,
    ClusterSuggestions,
    IdentityAck,
    RankedCluster,
    RankedClusters,
    RankingInputs,
    StatusAck,
    SupportAck,
    ValidateReport,
)
from app.persistence.audit import SqlAuditWriter
from app.persistence.lifecycle import SqlTransitionStore
from app.shared.enums import ProblemStatus as Status
from app.shared.geo import cluster_radius_m, distance_m


def read_district(principal: Principal) -> UUID | None:
    if principal.role == Role.SUPER_ADMIN:
        return None
    if principal.district_id is None:
        raise PermissionDeniedError("Your account has no assigned district.")
    return principal.district_id


def _panchayat(principal: Principal) -> None:
    if principal.role != Role.PANCHAYAT:
        raise PermissionDeniedError("Only Panchayat accounts can validate and cluster reports.")
    read_district(principal)


async def validate_report(
    session: AsyncSession, principal: Principal, report_id: UUID, body: ValidateReport
) -> StatusAck:
    _panchayat(principal)
    snapshot = await SqlTransitionStore().transition(
        session,
        report_id,
        Status.REPORTED,
        Status.VERIFIED if body.decision == "verify" else Status.REJECTED,
        actor=principal,
        reason=body.reason,
    )
    report = await session.get(Report, report_id)
    if report is not None:
        await publish_case_update(
            session,
            [report.reporter_id],
            event_key=f"report.status.{snapshot.status}",
            title="Your report was reviewed",
            body=f"Report {report.code} is now {snapshot.status.replace('_', ' ')}.",
            resource_type="report",
            resource_id=report.id,
        )
    return StatusAck(id=report_id, status=snapshot.status)


async def assign_cluster(
    session: AsyncSession, principal: Principal, report_id: UUID, body: AssignCluster
) -> StatusAck:
    _panchayat(principal)
    snapshot = await SqlTransitionStore().transition(
        session,
        report_id,
        Status.VERIFIED,
        Status.PRIORITISED,
        actor=principal,
        reason=None,
        cluster_id=body.cluster_id,
    )
    report = await session.get(Report, report_id)
    if report is not None:
        await publish_case_update(
            session,
            [report.reporter_id],
            event_key=f"report.status.{snapshot.status}",
            title="Your report joined a community case",
            body=f"Report {report.code} is now part of a tracked community case.",
            resource_type="report",
            resource_id=report.id,
        )
    return StatusAck(id=report_id, status=snapshot.status)


async def _snapshots(session: AsyncSession, principal: Principal) -> list[ClusterSnapshot]:
    district = read_district(principal)
    rows = await cluster_snapshots(session, district)
    if principal.role in {Role.DEPARTMENT, Role.OFFICER}:
        if district is None or principal.department_id is None:
            raise PermissionDeniedError("Your account has no assigned department.")
        categories = await department_categories(session, district, principal.department_id)
        rows = [row for row in rows if row.cluster.category in categories]
    return rows


async def suggestions(
    session: AsyncSession, principal: Principal, report_id: UUID
) -> ClusterSuggestions:
    _panchayat(principal)
    report = await session.get(Report, report_id)
    if report is None:
        raise NotFoundError("Report not found.")
    require_district(principal, report.district_id)
    if report.status != Status.VERIFIED or report.cluster_id is not None:
        raise ConflictError("Validate the report before selecting a cluster.")
    items = []
    for row in await _snapshots(session, principal):
        if (
            row.cluster.category != report.category
            or row.cluster.status not in JOINABLE_CLUSTER_STATUSES
        ):
            continue
        distance = distance_m(
            report.latitude, report.longitude, row.anchor.latitude, row.anchor.longitude
        )
        if distance <= cluster_radius_m(report.category):
            items.append(
                ClusterSuggestion(
                    id=row.cluster.id,
                    title=row.anchor.title,
                    category=row.cluster.category,
                    distance_m=distance,
                    report_count=row.report_count,
                    supporter_count=row.supporter_count,
                )
            )
    items.sort(key=lambda item: (item.distance_m, item.id))
    return ClusterSuggestions(items=items)


async def ranking_view(
    session: AsyncSession, principal: Principal
) -> tuple[RankedClusters, dict[UUID, int]]:
    """The ranked list plus community support for every cluster in scope.

    Only `prioritised` clusters — open demand still waiting for funding — are
    ranked. Funded, in-progress and verified work leaves the ranking, so a
    finished repair cannot hold a top place or inflate "ranked N of M".
    """
    rows = await _snapshots(session, principal)
    supporters = {row.cluster.id: row.supporter_count for row in rows}
    now = datetime.now(UTC)
    scored = []
    for row in rows:
        cluster = row.cluster
        if cluster.status != Status.PRIORITISED:
            continue
        score, breakdown = score_cluster(
            supporters=row.supporter_count,
            severity=row.severity,
            anchor_created_at=row.anchor.created_at,
            now=now,
            gap=cluster.infrastructure_gap,
            equity=cluster.equity_index,
            inputs_are_demo=cluster.inputs_are_demo,
        )
        scored.append((score, row, breakdown))
    scored.sort(key=lambda item: (-item[0], item[1].anchor.created_at, item[1].cluster.id))
    ranked = RankedClusters(
        items=[
            RankedCluster(
                id=row.cluster.id,
                title=row.anchor.title,
                category=row.cluster.category,
                status=row.cluster.status,
                rank=rank,
                priority_score=score,
                supporter_count=row.supporter_count,
                report_count=row.report_count,
                anchor_report_code=row.anchor.code,
                infrastructure_gap=50
                if row.cluster.infrastructure_gap is None
                else row.cluster.infrastructure_gap,
                equity_index=50 if row.cluster.equity_index is None else row.cluster.equity_index,
                inputs_are_demo=(
                    row.cluster.inputs_are_demo
                    or row.cluster.infrastructure_gap is None
                    or row.cluster.equity_index is None
                ),
                score_breakdown=breakdown,
            )
            for rank, (score, row, breakdown) in enumerate(scored, 1)
        ]
    )
    return ranked, supporters


async def ranked_clusters(session: AsyncSession, principal: Principal) -> RankedClusters:
    ranked, _ = await ranking_view(session, principal)
    return ranked


async def update_inputs(
    session: AsyncSession, principal: Principal, cluster_id: UUID, body: RankingInputs
) -> IdentityAck:
    if principal.role not in {Role.DEPARTMENT, Role.GOV_ADMIN, Role.SUPER_ADMIN}:
        raise PermissionDeniedError(
            "Only the responsible department or an administrator can set inputs."
        )
    cluster = await session.scalar(
        select(Cluster)
        .where(Cluster.id == cluster_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if cluster is None:
        raise NotFoundError("Cluster not found.")
    require_district(principal, cluster.district_id)
    if principal.role == Role.DEPARTMENT:
        owner = await responsible_department(session, cluster.district_id, cluster.category)
        if owner is None or owner != principal.department_id:
            raise NotFoundError("Cluster not found.")
    before = {
        "infrastructure_gap": cluster.infrastructure_gap,
        "equity_index": cluster.equity_index,
        "inputs_are_demo": cluster.inputs_are_demo,
    }
    cluster.infrastructure_gap = body.infrastructure_gap
    cluster.equity_index = body.equity_index
    cluster.inputs_are_demo = False
    await SqlAuditWriter().log_event(
        session,
        AuditEvent(
            principal.user_id,
            "cluster.inputs_updated",
            "cluster",
            cluster.id,
            cluster.district_id,
            before=before,
            after={**body.model_dump(), "inputs_are_demo": False},
        ),
    )
    return IdentityAck(id=cluster.id)


async def support_cluster(
    session: AsyncSession, principal: Principal, cluster_id: UUID
) -> SupportAck:
    if principal.role != Role.CITIZEN:
        raise PermissionDeniedError("Only citizens can add community support.")
    read_district(principal)
    cluster = await session.scalar(
        select(Cluster).where(Cluster.id == cluster_id).with_for_update()
    )
    if cluster is None:
        raise NotFoundError("Cluster not found.")
    require_district(principal, cluster.district_id)
    if cluster.status not in JOINABLE_CLUSTER_STATUSES:
        raise ConflictError("This repair is already awaiting or past citizen verification.")
    added = await session.scalar(
        insert(Support)
        .values(cluster_id=cluster.id, user_id=principal.user_id, is_demo=principal.is_demo)
        .on_conflict_do_nothing(index_elements=["cluster_id", "user_id"])
        .returning(Support.id)
    )
    if added is not None:
        await SqlAuditWriter().log_event(
            session,
            AuditEvent(
                principal.user_id,
                "cluster.supported",
                "cluster",
                cluster.id,
                cluster.district_id,
                after={"supporter_id": str(principal.user_id)},
            ),
        )
    # The same UNION used by ranking counts reporters and explicit support once.
    rows = await cluster_snapshots(session, cluster.district_id)
    count = next(row.supporter_count for row in rows if row.cluster.id == cluster.id)
    return SupportAck(id=cluster.id, supporter_count=count)
