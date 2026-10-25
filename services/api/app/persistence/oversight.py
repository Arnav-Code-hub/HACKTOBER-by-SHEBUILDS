"""Scoped aggregate queries and atomic privileged user changes."""

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditEvent
from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from app.core.roles import Role
from app.core.security import Principal
from app.modules.audit.models import AuditEventRecord
from app.modules.audit.schemas import (
    AdminSummary,
    AdminUserChange,
    AdminUserList,
    AdminUserRead,
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


async def audit_list(session: AsyncSession, principal: Principal, limit: int) -> AuditList:
    require_admin(principal)
    query = select(AuditEventRecord, User.display_name).join(
        User, AuditEventRecord.actor_id == User.id
    )
    if principal.role != Role.SUPER_ADMIN:
        query = query.where(AuditEventRecord.district_id == principal.district_id)
    rows = (
        await session.execute(
            query.order_by(AuditEventRecord.created_at.desc(), AuditEventRecord.id.desc()).limit(
                limit
            )
        )
    ).all()
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
            )
            for e, name in rows
        ]
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
