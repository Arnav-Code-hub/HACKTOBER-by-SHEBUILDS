"""Public organization-scope validation used during identity resolution."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import PermissionDeniedError
from app.modules.departments.models import DepartmentCategory, Organization


async def responsible_department(
    session: AsyncSession, district_id: UUID, category: str
) -> UUID | None:
    return (
        await session.scalars(
            select(DepartmentCategory.department_id).where(
                DepartmentCategory.district_id == district_id,
                DepartmentCategory.category == category,
            )
        )
    ).one_or_none()


async def department_categories(
    session: AsyncSession, district_id: UUID, department_id: UUID
) -> list[str]:
    return list(
        await session.scalars(
            select(DepartmentCategory.category).where(
                DepartmentCategory.district_id == district_id,
                DepartmentCategory.department_id == department_id,
            )
        )
    )


async def district_name(session: AsyncSession, district_id: UUID) -> str:
    value = await session.scalar(
        select(Organization.name).where(
            Organization.id == district_id,
            Organization.type == "district",
            Organization.is_active.is_(True),
        )
    )
    if value is None:
        raise PermissionDeniedError("Your assigned district is unavailable.")
    return value


async def validate_active_scope(
    session: AsyncSession,
    district_id: UUID | None,
    scopes: dict[str, UUID | None],
) -> None:
    expected = {kind: identity for kind, identity in scopes.items() if identity is not None}
    if district_id is not None:
        expected["district"] = district_id
    if not expected:
        return
    organizations = (
        await session.scalars(select(Organization).where(Organization.id.in_(expected.values())))
    ).all()
    indexed = {row.id: row for row in organizations}
    if any(
        identity not in indexed
        or not indexed[identity].is_active
        or indexed[identity].type != kind
        or (kind != "district" and indexed[identity].parent_id != district_id)
        for kind, identity in expected.items()
    ):
        raise PermissionDeniedError("Your account's organization scope is unavailable.")
