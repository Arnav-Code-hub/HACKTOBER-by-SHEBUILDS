"""Citizen report persistence using the shared transaction and media services."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditEvent
from app.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from app.core.idempotency import RequestIdentity, StoredResponse, request_hash
from app.core.lifecycle import StatusSnapshot, effective_status
from app.core.roles import Role
from app.core.security import Principal
from app.integrations.cloudinary import MediaProvider
from app.modules.departments.service import department_categories, district_name
from app.modules.files.service import attach_report_media, report_media
from app.modules.problems.clusters import ranking_view, read_district
from app.modules.problems.models import Cluster, Report
from app.modules.problems.schemas import RankedCluster, ReportCreate, ReportList, ReportRead
from app.persistence.audit import SqlAuditWriter
from app.persistence.idempotency import SqlIdempotencyStore
from app.shared.enums import ProblemStatus


def _citizen(principal: Principal) -> UUID:
    if principal.role != Role.CITIZEN or principal.district_id is None:
        raise PermissionDeniedError("This account cannot use citizen report actions.")
    return principal.district_id


async def _read(
    session: AsyncSession,
    principal: Principal,
    provider: MediaProvider,
    *,
    report_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
    mine: bool = False,
    statuses: list[ProblemStatus] | None = None,
) -> list[ReportRead]:
    district = read_district(principal)
    if principal.role == Role.CITIZEN:
        mine = True
    elif principal.role not in {
        Role.PANCHAYAT,
        Role.DEPARTMENT,
        Role.OFFICER,
        Role.GOV_ADMIN,
        Role.SUPER_ADMIN,
    }:
        raise PermissionDeniedError("This account cannot read citizen reports.")
    query = select(
        Report,
        Cluster.status.label("execution_status"),
        Cluster.status_changed_at.label("execution_changed_at"),
    ).outerjoin(Cluster, Report.cluster_id == Cluster.id)
    if district is not None:
        query = query.where(Report.district_id == district)
    if mine:
        query = query.where(Report.reporter_id == principal.user_id)
    if principal.role in {Role.DEPARTMENT, Role.OFFICER}:
        if district is None or principal.department_id is None:
            raise PermissionDeniedError("Your account has no assigned department.")
        categories = await department_categories(session, district, principal.department_id)
        query = query.where(Report.category.in_(categories))
    if statuses is not None:
        query = query.where(func.coalesce(Cluster.status, Report.status).in_(statuses))
    if report_id is not None:
        query = query.where(Report.id == report_id)
    rows = (
        await session.execute(
            query.order_by(Report.created_at.desc(), Report.id.desc()).limit(limit).offset(offset)
        )
    ).all()
    if not rows:
        return []
    names = {
        district_id: await district_name(session, district_id)
        for district_id in {row.Report.district_id for row in rows}
    }
    photos = await report_media(session, [row.Report.id for row in rows], provider)
    ranked: dict[UUID, RankedCluster] = {}
    supporters: dict[UUID, int] = {}
    if any(row.Report.cluster_id for row in rows):
        ranking, supporters = await ranking_view(session, principal)
        ranked = {item.id: item for item in ranking.items}
    result = []
    for row in rows:
        cluster_rank = ranked.get(row.Report.cluster_id)
        snapshot = effective_status(
            StatusSnapshot(ProblemStatus(row.Report.status), row.Report.status_changed_at),
            StatusSnapshot(ProblemStatus(row.execution_status), row.execution_changed_at)
            if row.execution_status is not None
            else None,
        )
        assert snapshot.status_changed_at is not None  # Both source columns are NOT NULL.
        result.append(
            ReportRead(
                id=row.Report.id,
                code=row.Report.code,
                title=row.Report.title,
                description=row.Report.summary,
                transcript=row.Report.transcript,
                reporter_id=row.Report.reporter_id,
                category=row.Report.category,
                severity=row.Report.severity,
                status=snapshot.status,
                status_changed_at=snapshot.status_changed_at,
                ward=row.Report.location_label,
                district=names[row.Report.district_id],
                latitude=row.Report.latitude,
                longitude=row.Report.longitude,
                channel=row.Report.channel,
                created_at=row.Report.created_at,
                updated_at=row.Report.updated_at,
                rejection_reason=row.Report.rejection_reason,
                cluster_id=row.Report.cluster_id,
                is_demo=row.Report.is_demo,
                media=photos.get(row.Report.id, []),
                rank=cluster_rank.rank if cluster_rank else None,
                total_ranked=len(ranked) if cluster_rank else None,
                priority_score=cluster_rank.priority_score if cluster_rank else None,
                # Support stays visible after funding; rank does not.
                supporter_count=supporters.get(row.Report.cluster_id)
                if row.Report.cluster_id
                else None,
                score_breakdown=cluster_rank.score_breakdown if cluster_rank else None,
            )
        )
    return result


async def get_report(
    session: AsyncSession,
    principal: Principal,
    report_id: UUID,
    provider: MediaProvider,
) -> ReportRead:
    items = await _read(session, principal, provider, report_id=report_id)
    if not items:
        raise NotFoundError("Report not found.")
    return items[0]


async def list_reports(
    session: AsyncSession,
    principal: Principal,
    provider: MediaProvider,
    *,
    mine: bool | None,
    limit: int,
    offset: int,
    status: str | None = None,
) -> ReportList:
    if principal.role == Role.CITIZEN and mine is False:
        raise PermissionDeniedError("Citizens can read only their own reports.")
    statuses = None
    if status is not None:
        try:
            statuses = [ProblemStatus(value) for value in status.split("|")]
        except ValueError as exc:
            raise ValidationError("Choose an agreed report status.") from exc
    return ReportList(
        items=await _read(
            session,
            principal,
            provider,
            limit=limit,
            offset=offset,
            mine=bool(mine),
            statuses=statuses,
        )
    )


async def create_report(
    session: AsyncSession,
    principal: Principal,
    body: ReportCreate,
    key: str,
    provider: MediaProvider,
) -> StoredResponse:
    district = _citizen(principal)
    identity = RequestIdentity(
        principal.user_id, "reports.create", key, request_hash(body.model_dump(mode="json"))
    )

    async def action() -> StoredResponse:
        # Resolve trusted district before writing. Never accept reporter/district
        # identifiers from the submitted JSON, even when supplied as extra fields.
        await district_name(session, district)
        values = body.model_dump(exclude={"media_ids"})
        report = Report(
            reporter_id=principal.user_id, district_id=district, is_demo=principal.is_demo, **values
        )
        session.add(report)
        await session.flush()
        await attach_report_media(session, body.media_ids, principal.user_id, report.id)
        await SqlAuditWriter().log_event(
            session,
            AuditEvent(
                principal.user_id,
                "report.created",
                "report",
                report.id,
                district,
                after={"code": report.code, "status": "reported"},
            ),
        )
        dto = await get_report(session, principal, report.id, provider)
        return StoredResponse(201, dto.model_dump(mode="json"))

    return await SqlIdempotencyStore().execute(session, identity, action)
