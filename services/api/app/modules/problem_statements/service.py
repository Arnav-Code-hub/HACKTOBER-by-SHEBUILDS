"""Business logic for problem statements. THE PUBLIC FACE of this module.

A statement invites student solutions and CSR pledges against a local problem.
It is never a government work order and authorises no public repair.

Read access: partner and oversight roles see published statements only; a
department also sees its own drafts. Drafts never leave their department.

# Module boundary: other modules may import this file and schemas.py.
# They must NEVER import models.py or repository.py.
"""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditEvent
from app.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from app.core.idempotency import RequestIdentity, StoredResponse, request_hash
from app.core.permissions import Permission, has_permission
from app.core.roles import Role
from app.core.security import Principal
from app.modules.departments.service import responsible_department
from app.modules.problem_statements.models import ProblemStatement
from app.modules.problem_statements.schemas import StatementCreate, StatementList, StatementRead
from app.modules.problems.service import cluster_scope
from app.persistence.audit import SqlAuditWriter
from app.persistence.idempotency import SqlIdempotencyStore


def _department(principal: Principal) -> tuple[UUID, UUID]:
    if (
        principal.role != Role.DEPARTMENT
        or principal.district_id is None
        or principal.department_id is None
    ):
        raise PermissionDeniedError("Only a department can create or publish statements.")
    return principal.district_id, principal.department_id


async def list_statements(
    session: AsyncSession,
    principal: Principal,
    status: Literal["draft", "published"] | None = None,
) -> StatementList:
    query = select(ProblemStatement)
    if principal.role == Role.DEPARTMENT:
        district, department = _department(principal)
        query = query.where(
            ProblemStatement.district_id == district,
            or_(
                ProblemStatement.status == "published",
                ProblemStatement.department_id == department,
            ),
        )
    elif has_permission(principal.role, Permission.STATEMENT_READ_PUBLISHED):
        query = query.where(ProblemStatement.status == "published")
        if principal.role != Role.SUPER_ADMIN:
            if principal.district_id is None:
                raise PermissionDeniedError("Your account has no assigned district.")
            query = query.where(ProblemStatement.district_id == principal.district_id)
    else:
        raise PermissionDeniedError("This account cannot read problem statements.")
    if status is not None:
        query = query.where(ProblemStatement.status == status)
    rows = (
        await session.scalars(
            query.order_by(
                ProblemStatement.published_at.desc().nulls_last(),
                ProblemStatement.created_at.desc(),
                ProblemStatement.id,
            )
        )
    ).all()
    return StatementList(items=[StatementRead.model_validate(row) for row in rows])


async def create_statement(
    session: AsyncSession, principal: Principal, body: StatementCreate, key: str
) -> StoredResponse:
    district, department = _department(principal)
    identity = RequestIdentity(
        principal.user_id, "statements.create", key, request_hash(body.model_dump(mode="json"))
    )

    async def action() -> StoredResponse:
        if body.cluster_id is not None:
            scope = await cluster_scope(session, body.cluster_id)
            if scope is None or scope[0] != district:
                raise ValidationError("Link a cluster from your own district.")
            if await responsible_department(session, district, scope[1]) != department:
                raise ValidationError("Link a cluster your department is responsible for.")
        statement = ProblemStatement(
            department_id=department,
            district_id=district,
            created_by=principal.user_id,
            cluster_id=body.cluster_id,
            title=body.title,
            body=body.body,
            status="draft",
            is_demo=principal.is_demo,
        )
        session.add(statement)
        await session.flush()
        await SqlAuditWriter().log_event(
            session,
            AuditEvent(
                principal.user_id,
                "statement.created",
                "statement",
                statement.id,
                district,
                after={"title": statement.title, "status": "draft"},
            ),
        )
        read = StatementRead.model_validate(statement)
        return StoredResponse(201, read.model_dump(mode="json"))

    return await SqlIdempotencyStore().execute(session, identity, action)


async def publish_statement(
    session: AsyncSession, principal: Principal, statement_id: UUID
) -> StatementRead:
    district, department = _department(principal)
    statement = await session.scalar(
        select(ProblemStatement)
        .where(ProblemStatement.id == statement_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        statement is None
        or statement.district_id != district
        or statement.department_id != department
    ):
        raise NotFoundError("Statement not found.")
    if statement.status == "draft":
        statement.status = "published"
        statement.published_at = datetime.now(UTC)
        await SqlAuditWriter().log_event(
            session,
            AuditEvent(
                principal.user_id,
                "statement.published",
                "statement",
                statement.id,
                district,
                before={"status": "draft"},
                after={"status": "published"},
            ),
        )
    # Publishing twice returns the already-published statement.
    return StatementRead.model_validate(statement)
