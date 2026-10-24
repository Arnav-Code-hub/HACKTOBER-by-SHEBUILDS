"""Record-scope checks. Permissions are checked separately, before these rules."""

from uuid import UUID

from app.core.errors import NotFoundError
from app.core.roles import Role
from app.core.security import Principal


def require_district(principal: Principal, district_id: UUID) -> None:
    if principal.role != Role.SUPER_ADMIN and principal.district_id != district_id:
        raise NotFoundError("Record not found.")


def require_department(principal: Principal, district_id: UUID, department_id: UUID) -> None:
    require_district(principal, district_id)
    if principal.role != Role.SUPER_ADMIN and principal.department_id != department_id:
        raise NotFoundError("Record not found.")


def require_institute(principal: Principal, institute_id: UUID) -> None:
    if principal.role != Role.SUPER_ADMIN and principal.institute_id != institute_id:
        raise NotFoundError("Record not found.")


def require_owner(principal: Principal, owner_id: UUID) -> None:
    # No implicit admin bypass: original-reporter verification must stay strict.
    if principal.user_id != owner_id:
        raise NotFoundError("Record not found.")


def require_assignment(
    principal: Principal, district_id: UUID, department_id: UUID, officer_id: UUID
) -> None:
    require_department(principal, district_id, department_id)
    require_owner(principal, officer_id)
