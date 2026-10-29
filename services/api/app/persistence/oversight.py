"""Scoped aggregate queries and atomic privileged user changes."""

from typing import Any
from uuid import UUID

from sqlalchemy import case, func, literal, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.audit import AuditEvent
from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from app.core.roles import Role
from app.core.security import Principal
from app.modules.analytics.schemas import (
    DistrictTransparency,
    PublicTransparency,
    StaffWorkload,
    StaffWorkloadList,
)
from app.modules.audit.models import AuditEventRecord
from app.modules.audit.schemas import (
    AdminSummary,
    AdminUserChange,
    AdminUserList,
    AdminUserRead,
    AdminUserStatusChange,
    AuditCursor,
    AuditList,
    AuditRead,
    OrganizationList,
    OrganizationRead,
)
from app.modules.departments.models import Organization
from app.modules.funding.models import Allocation, Sponsorship
from app.modules.problem_statements.models import ProblemStatement
from app.modules.problems.models import Cluster, Report, WorkOrder
from app.modules.users.models import User
from app.modules.users.service import validate_scope
from app.persistence.audit import SqlAuditWriter
from app.shared.enums import ProblemStatus as Status

# Work an officer still has to carry out or see verified.
OPEN_WORK = (Status.FUNDED, Status.IN_PROGRESS, Status.AWAITING_VERIFICATION)
ACTIVE_CASES = tuple(status for status in Status if status != Status.CITIZEN_VERIFIED)


def require_admin(principal: Principal, *, super_only: bool = False) -> None:
    allowed = {Role.SUPER_ADMIN} if super_only else {Role.SUPER_ADMIN, Role.GOV_ADMIN}
    if principal.role not in allowed:
        raise PermissionDeniedError("Administrator access required.")
    if principal.role == Role.GOV_ADMIN and principal.district_id is None:
        raise PermissionDeniedError("Your account has no district.")


async def summary(session: AsyncSession, principal: Principal) -> AdminSummary:
    require_admin(principal)
    status = func.coalesce(Cluster.status, Report.status)
    reports = (
        select(status, func.count())
        .select_from(Report)
        .outerjoin(Cluster, Report.cluster_id == Cluster.id)
    )
    orders = (
        select(Cluster.status, func.count())
        .select_from(WorkOrder)
        .join(Cluster, WorkOrder.cluster_id == Cluster.id)
    )
    clusters = select(func.count()).select_from(Cluster)
    allocations = (
        select(func.coalesce(func.sum(Allocation.amount_paise), 0))
        .select_from(Allocation)
        .join(Cluster, Allocation.cluster_id == Cluster.id)
    )
    pledges = (
        select(func.coalesce(func.sum(Sponsorship.amount_paise), 0))
        .select_from(Sponsorship)
        .join(ProblemStatement, Sponsorship.statement_id == ProblemStatement.id)
    )
    name = "All districts"
    if principal.role != Role.SUPER_ADMIN:
        district = principal.district_id
        reports = reports.where(Report.district_id == district)
        orders = orders.where(WorkOrder.district_id == district)
        clusters = clusters.where(Cluster.district_id == district)
        allocations = allocations.where(Cluster.district_id == district)
        pledges = pledges.where(ProblemStatement.district_id == district)
        name = (
            await session.scalar(select(Organization.name).where(Organization.id == district)) or ""
        )
    return AdminSummary(
        district_name=name,
        reports_by_status={
            str(k): v for k, v in (await session.execute(reports.group_by(status))).all()
        },
        cluster_count=await session.scalar(clusters) or 0,
        work_orders_by_status={
            str(k): v for k, v in (await session.execute(orders.group_by(Cluster.status))).all()
        },
        allocated_paise=int(await session.scalar(allocations) or 0),
        pledged_paise=int(await session.scalar(pledges) or 0),
    )


async def public_transparency(session: AsyncSession) -> PublicTransparency:
    """Publish aggregate live records only; never expose reporters or coordinates."""
    report_counts: dict[str, int] = {
        str(status): int(total)
        for status, total in (
            await session.execute(
                select(Report.status, func.count())
                .where(Report.is_demo.is_(False))
                .group_by(Report.status)
            )
        ).all()
    }
    cluster_counts: dict[str, int] = {
        str(status): int(total)
        for status, total in (
            await session.execute(
                select(Cluster.status, func.count())
                .where(Cluster.is_demo.is_(False))
                .group_by(Cluster.status)
            )
        ).all()
    }
    report_rows = (
        await session.execute(
            select(
                Report.district_id,
                func.count().label("total"),
                func.max(Report.status_changed_at).label("updated_at"),
            )
            .where(Report.is_demo.is_(False))
            .group_by(Report.district_id)
        )
    ).all()
    cluster_rows = (
        await session.execute(
            select(
                Cluster.district_id,
                func.count().label("total"),
                func.count().filter(Cluster.status.in_(ACTIVE_CASES)).label("active"),
                func.count().filter(Cluster.status == Status.CITIZEN_VERIFIED).label("verified"),
                func.max(Cluster.status_changed_at).label("updated_at"),
            )
            .where(Cluster.is_demo.is_(False))
            .group_by(Cluster.district_id)
        )
    ).all()
    allocation_rows = (
        await session.execute(
            select(Cluster.district_id, func.coalesce(func.sum(Allocation.amount_paise), 0))
            .select_from(Allocation)
            .join(Cluster, Allocation.cluster_id == Cluster.id)
            .where(Allocation.is_demo.is_(False), Cluster.is_demo.is_(False))
            .group_by(Cluster.district_id)
        )
    ).all()
    districts = (
        await session.execute(
            select(Organization.id, Organization.name)
            .where(
                Organization.type == "district",
                Organization.is_active.is_(True),
                Organization.is_demo.is_(False),
            )
            .order_by(Organization.name, Organization.id)
        )
    ).all()

    by_report = {row.district_id: row for row in report_rows}
    by_cluster = {row.district_id: row for row in cluster_rows}
    by_allocation: dict[UUID, int] = {
        district_id: int(amount) for district_id, amount in allocation_rows
    }
    rows = []
    for district_id, name in districts:
        reports = by_report.get(district_id)
        clusters = by_cluster.get(district_id)
        updated = [
            value
            for value in (
                reports.updated_at if reports else None,
                clusters.updated_at if clusters else None,
            )
            if value is not None
        ]
        rows.append(
            DistrictTransparency(
                district_name=name,
                report_count=reports.total if reports else 0,
                cluster_count=clusters.total if clusters else 0,
                active_cases=clusters.active if clusters else 0,
                citizen_verified_cases=clusters.verified if clusters else 0,
                allocated_paise=by_allocation.get(district_id, 0),
                last_updated=max(updated) if updated else None,
            )
        )
    updated_at = max((row.last_updated for row in rows if row.last_updated), default=None)
    active_cases = sum(cluster_counts.get(status, 0) for status in ACTIVE_CASES)
    verified = cluster_counts.get(Status.CITIZEN_VERIFIED, 0)
    allocated = sum(by_allocation.values())
    return PublicTransparency(
        updated_at=updated_at,
        report_count=sum(report_counts.values()),
        cluster_count=sum(cluster_counts.values()),
        active_cases=active_cases,
        citizen_verified_cases=verified,
        allocated_paise=allocated,
        reports_by_status=report_counts,
        clusters_by_status=cluster_counts,
        districts=rows,
    )


async def staff_workload(
    session: AsyncSession,
    principal: Principal,
) -> StaffWorkloadList:
    if principal.role not in {Role.DEPARTMENT, Role.GOV_ADMIN, Role.SUPER_ADMIN}:
        raise PermissionDeniedError("Department or administrator access required.")
    if principal.role in {Role.DEPARTMENT, Role.GOV_ADMIN} and principal.district_id is None:
        raise PermissionDeniedError("Your account has no assigned district.")
    department = aliased(Organization)
    live_work = WorkOrder.is_demo.is_(False) & Cluster.is_demo.is_(False)
    funded = func.count(WorkOrder.id).filter(live_work, Cluster.status == Status.FUNDED)
    in_progress = func.count(WorkOrder.id).filter(live_work, Cluster.status == Status.IN_PROGRESS)
    awaiting = func.count(WorkOrder.id).filter(
        live_work, Cluster.status == Status.AWAITING_VERIFICATION
    )
    open_count = func.count(WorkOrder.id).filter(live_work, Cluster.status.in_(OPEN_WORK))
    oldest = func.min(case((live_work & Cluster.status.in_(OPEN_WORK), WorkOrder.assigned_at)))
    query = (
        select(
            User.id,
            User.display_name,
            User.email,
            department.name,
            open_count,
            funded,
            in_progress,
            awaiting,
            oldest,
        )
        .select_from(User)
        .outerjoin(WorkOrder, WorkOrder.officer_id == User.id)
        .outerjoin(Cluster, Cluster.id == WorkOrder.cluster_id)
        .outerjoin(department, department.id == User.department_id)
        .where(User.role == Role.OFFICER, User.is_active.is_(True), User.is_demo.is_(False))
        .group_by(User.id, department.name)
        .order_by(open_count.desc(), User.display_name, User.id)
    )
    if principal.role != Role.SUPER_ADMIN:
        query = query.where(User.district_id == principal.district_id)
    if principal.role == Role.DEPARTMENT:
        if principal.department_id is None:
            raise PermissionDeniedError("Your account has no assigned department.")
        query = query.where(User.department_id == principal.department_id)
    result = await session.execute(query)
    return StaffWorkloadList(
        items=[
            StaffWorkload(
                user_id=row[0],
                display_name=row[1],
                email=row[2],
                department_name=row[3],
                open_work_orders=row[4] or 0,
                funded=row[5] or 0,
                in_progress=row[6] or 0,
                awaiting_verification=row[7] or 0,
                oldest_open_assignment=row[8],
            )
            for row in result.all()
        ]
    )


# Contact details stay out of audit views; the users list is super-admin only.
PRIVATE_AUDIT_KEYS = frozenset({"email"})


def _public(values: dict[str, Any] | None) -> dict[str, Any] | None:
    if values is None:
        return None
    return {key: value for key, value in values.items() if key not in PRIVATE_AUDIT_KEYS}


async def audit_list(
    session: AsyncSession,
    principal: Principal,
    limit: int,
    before: AuditCursor | None = None,
) -> AuditList:
    require_admin(principal)
    query = select(AuditEventRecord, User.display_name).join(
        User, AuditEventRecord.actor_id == User.id
    )
    if principal.role != Role.SUPER_ADMIN:
        query = query.where(AuditEventRecord.district_id == principal.district_id)
    if before is not None:
        # Keyset paging on the same (time, id) order: no gaps or repeats when
        # new events arrive between pages.
        query = query.where(
            tuple_(AuditEventRecord.created_at, AuditEventRecord.id)
            < tuple_(literal(before.before_at), literal(before.before_id))
        )
    rows = (
        await session.execute(
            query.order_by(AuditEventRecord.created_at.desc(), AuditEventRecord.id.desc()).limit(
                limit + 1
            )
        )
    ).all()
    page, more = rows[:limit], len(rows) > limit
    last = page[-1][0] if page else None
    return AuditList(
        items=[
            AuditRead(
                id=e.id,
                at=e.created_at,
                actor_name=name,
                actor_role=e.actor_role,
                action=e.action,
                entity_type=e.entity_type,
                entity_id=e.entity_id,
                reason=e.reason,
                before=_public(e.before),
                after=_public(e.after),
            )
            for e, name in page
        ],
        next=AuditCursor(before_at=last.created_at, before_id=last.id) if more and last else None,
    )


async def users(session: AsyncSession, principal: Principal) -> AdminUserList:
    require_admin(principal, super_only=True)
    rows = (await session.scalars(select(User).order_by(User.display_name, User.id))).all()
    return AdminUserList(items=[AdminUserRead.model_validate(row) for row in rows])


async def organizations(session: AsyncSession, principal: Principal) -> OrganizationList:
    require_admin(principal, super_only=True)
    rows = (
        await session.scalars(
            select(Organization)
            .where(Organization.is_active.is_(True))
            .order_by(Organization.type, Organization.name, Organization.id)
        )
    ).all()
    return OrganizationList(items=[OrganizationRead.model_validate(row) for row in rows])


async def change_user(
    session: AsyncSession, principal: Principal, identity: UUID, body: AdminUserChange
) -> AdminUserRead:
    require_admin(principal, super_only=True)
    if identity == principal.user_id:
        raise PermissionDeniedError("Another super administrator must change your role or scope.")
    user = await session.scalar(
        select(User)
        .where(User.id == identity)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if user is None:
        raise NotFoundError("User not found.")
    before = AdminUserRead.model_validate(user).model_dump(mode="json")
    user.role = body.role
    user.district_id = body.district_id
    user.department_id = (
        body.department_id if body.role in {Role.DEPARTMENT, Role.OFFICER} else None
    )
    user.institute_id = (
        body.institute_id if body.role in {Role.STUDENT, Role.FACULTY, Role.INSTITUTE} else None
    )
    user.organization_id = body.organization_id if body.role == Role.INDUSTRY else None
    # The row lock above serialises this with funding, which share-locks the
    # officer it assigns, so no new assignment can appear after this check.
    open_work = (
        select(func.count())
        .select_from(WorkOrder)
        .join(Cluster, WorkOrder.cluster_id == Cluster.id)
        .where(WorkOrder.officer_id == user.id, Cluster.status.in_(OPEN_WORK))
    )
    if user.role == Role.OFFICER:
        # Still an officer: only orders outside the new scope are stranded.
        open_work = open_work.where(
            or_(
                WorkOrder.district_id.is_distinct_from(user.district_id),
                WorkOrder.department_id.is_distinct_from(user.department_id),
            )
        )
    with session.no_autoflush:
        stranded = await session.scalar(open_work)
    if stranded:
        raise ConflictError(
            f"This officer has {stranded} open work order(s) in their current department. "
            "They must be completed and verified before this change."
        )
    try:
        # Validate proposed foreign keys before any autoflush can persist them.
        with session.no_autoflush:
            await validate_scope(session, user.id)
    except PermissionDeniedError as exc:
        raise ValidationError(
            "Assign an active district and the organization required by this role."
        ) from exc
    after = AdminUserRead.model_validate(user)
    payload = after.model_dump(mode="json")
    if before != payload:
        # A move affects both districts; preserve visibility in each scope.
        for district in sorted(
            {before["district_id"], payload["district_id"]}, key=lambda v: v or ""
        ):
            await SqlAuditWriter().log_event(
                session,
                AuditEvent(
                    principal.user_id,
                    "user.scope_changed",
                    "user",
                    user.id,
                    UUID(district) if district else None,
                    before=before,
                    after=payload,
                    reason=body.reason,
                ),
            )
    return after


async def change_user_status(
    session: AsyncSession,
    principal: Principal,
    identity: UUID,
    body: AdminUserStatusChange,
) -> AdminUserRead:
    require_admin(principal, super_only=True)
    if identity == principal.user_id and not body.is_active:
        raise PermissionDeniedError("Another super administrator must deactivate your account.")
    user = await session.scalar(
        select(User)
        .where(User.id == identity)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if user is None:
        raise NotFoundError("User not found.")
    if user.is_active == body.is_active:
        return AdminUserRead.model_validate(user)
    if not body.is_active and user.role == Role.OFFICER:
        open_work = await session.scalar(
            select(func.count())
            .select_from(WorkOrder)
            .join(Cluster, WorkOrder.cluster_id == Cluster.id)
            .where(WorkOrder.officer_id == identity, Cluster.status.in_(OPEN_WORK))
        )
        if open_work:
            raise ConflictError(
                "Complete, reassign or verify this officer's open work before deactivation."
            )
    before = AdminUserRead.model_validate(user).model_dump(mode="json")
    user.is_active = body.is_active
    after = AdminUserRead.model_validate(user)
    await SqlAuditWriter().log_event(
        session,
        AuditEvent(
            principal.user_id,
            "user.activated" if body.is_active else "user.deactivated",
            "user",
            user.id,
            user.district_id,
            before=before,
            after=after.model_dump(mode="json"),
            reason=body.reason,
        ),
    )
    return after
