"""Case tracker: every case from prioritisation to citizen verification.

Joins clusters, work orders, allocations, departments and users, so it lives
with the other cross-module read models rather than in one module.
"""

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.errors import PermissionDeniedError
from app.core.roles import Role
from app.core.security import Principal
from app.modules.departments.models import DepartmentCategory, Organization
from app.modules.funding.models import Allocation
from app.modules.problems.models import Cluster, Report, WorkOrder
from app.modules.problems.schemas import CaseList, CaseRead, WaitingOn
from app.modules.users.models import User
from app.shared.categories import Category
from app.shared.enums import ProblemStatus as Status

WAITING_ON: dict[Status, WaitingOn] = {
    Status.PRIORITISED: "department",
    Status.FUNDED: "officer",
    Status.IN_PROGRESS: "officer",
    Status.AWAITING_VERIFICATION: "citizen",
    Status.CITIZEN_VERIFIED: "none",
}


async def case_list(session: AsyncSession, principal: Principal, limit: int) -> CaseList:
    """Department: cases it must fund or has funded. Gov admin: its district.

    Super admin: every district. Other roles are refused.
    """
    role = principal.role
    if role not in {Role.DEPARTMENT, Role.GOV_ADMIN, Role.SUPER_ADMIN}:
        raise PermissionDeniedError("Only departments and administrators track cases.")
    if role != Role.SUPER_ADMIN and principal.district_id is None:
        raise PermissionDeniedError("Your account has no district.")
    if role == Role.DEPARTMENT and principal.department_id is None:
        raise PermissionDeniedError("Your account has no department.")

    officer = aliased(User)
    recorder = aliased(User)
    query = (
        select(
            Cluster,
            Report,
            WorkOrder,
            Allocation,
            Organization.name,
            officer.display_name,
            recorder.display_name,
        )
        .join(Report, Cluster.anchor_report_id == Report.id)
        .outerjoin(WorkOrder, WorkOrder.cluster_id == Cluster.id)
        .outerjoin(Allocation, Allocation.work_order_id == WorkOrder.id)
        .outerjoin(Organization, Organization.id == WorkOrder.department_id)
        .outerjoin(officer, officer.id == WorkOrder.officer_id)
        .outerjoin(recorder, recorder.id == Allocation.allocated_by)
        .where(Cluster.status.in_(list(WAITING_ON)))
    )
    if role != Role.SUPER_ADMIN:
        query = query.where(Cluster.district_id == principal.district_id)
    if role == Role.DEPARTMENT:
        responsible = select(DepartmentCategory.category).where(
            DepartmentCategory.department_id == principal.department_id,
            DepartmentCategory.district_id == principal.district_id,
        )
        query = query.where(
            or_(
                WorkOrder.department_id == principal.department_id,
                # Not funded yet: the categories this department answers for.
                and_(WorkOrder.id.is_(None), Cluster.category.in_(responsible)),
            )
        )
    rows = (
        await session.execute(
            query.order_by(Cluster.status_changed_at.desc(), Cluster.id).limit(limit)
        )
    ).all()
    return CaseList(
        items=[
            CaseRead(
                cluster_id=cluster.id,
                report_code=report.code,
                title=report.title,
                category=Category(cluster.category),
                status=Status(cluster.status),
                waiting_on=WAITING_ON[Status(cluster.status)],
                status_changed_at=cluster.status_changed_at,
                work_order_id=work.id if work else None,
                round=work.round if work else None,
                department_name=department,
                officer_name=officer_name,
                allocated_paise=allocation.amount_paise if allocation else None,
                allocated_at=allocation.created_at if allocation else None,
                allocated_by_name=recorder_name,
            )
            for cluster, report, work, allocation, department, officer_name, recorder_name in rows
        ]
    )
