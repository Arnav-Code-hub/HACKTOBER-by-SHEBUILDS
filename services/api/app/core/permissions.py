"""Roles, permissions and the dependency guards that enforce them.

This is the authoritative permission matrix for the platform. `docs/product/roles.md`
documents it in prose; this file is what actually runs. The web middleware mirrors
it for UX only — authorisation is enforced here, server-side, always.
"""

from enum import StrEnum

from fastapi import Depends, HTTPException, status

from app.core.roles import Role
from app.core.security import Principal, get_current_principal


class Permission(StrEnum):
    """Fine-grained capabilities. Endpoints require permissions, never roles.

    Requiring a permission rather than a role is what lets you add a role later
    without editing every endpoint.
    """

    PROBLEM_CREATE = "problem:create"
    PROBLEM_READ = "problem:read"
    PROBLEM_MODERATE = "problem:moderate"
    PROBLEM_VERIFY = "problem:verify"

    STATEMENT_CREATE = "statement:create"
    STATEMENT_PUBLISH = "statement:publish"

    PROJECT_CREATE = "project:create"
    PROJECT_REVIEW = "project:review"
    PROJECT_APPROVE = "project:approve"

    TEAM_MANAGE = "team:manage"
    BUILDFOLIO_ENDORSE = "buildfolio:endorse"

    FUNDING_ALLOCATE = "funding:allocate"
    FUNDING_DISBURSE = "funding:disburse"
    FUNDING_SPONSOR = "funding:sponsor"

    ANALYTICS_VIEW = "analytics:view"
    ANALYTICS_VIEW_ALL = "analytics:view_all"

    USER_MANAGE = "user:manage"
    ROLE_ASSIGN = "role:assign"
    AUDIT_READ = "audit:read"
    SYSTEM_CONFIGURE = "system:configure"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.CITIZEN: frozenset(
        {
            Permission.PROBLEM_CREATE,
            Permission.PROBLEM_READ,
            Permission.PROBLEM_VERIFY,
        }
    ),
    Role.STUDENT: frozenset(
        {
            Permission.PROBLEM_READ,
            Permission.PROJECT_CREATE,
            Permission.TEAM_MANAGE,
        }
    ),
    Role.FACULTY: frozenset(
        {
            Permission.PROBLEM_READ,
            Permission.PROJECT_REVIEW,
            Permission.BUILDFOLIO_ENDORSE,
            Permission.ANALYTICS_VIEW,
        }
    ),
    Role.INSTITUTE: frozenset(
        {
            Permission.PROBLEM_READ,
            Permission.PROJECT_REVIEW,
            Permission.ANALYTICS_VIEW,
            Permission.USER_MANAGE,
        }
    ),
    Role.PANCHAYAT: frozenset(
        {
            Permission.PROBLEM_READ,
            Permission.PROBLEM_MODERATE,
            Permission.PROBLEM_VERIFY,
            Permission.ANALYTICS_VIEW,
        }
    ),
    Role.DEPARTMENT: frozenset(
        {
            Permission.PROBLEM_READ,
            Permission.STATEMENT_CREATE,
            Permission.STATEMENT_PUBLISH,
            Permission.PROJECT_APPROVE,
            Permission.FUNDING_ALLOCATE,
            Permission.ANALYTICS_VIEW,
        }
    ),
    Role.OFFICER: frozenset(
        {
            Permission.PROBLEM_READ,
            Permission.PROBLEM_MODERATE,
            Permission.PROBLEM_VERIFY,
        }
    ),
    Role.INDUSTRY: frozenset(
        {
            Permission.PROBLEM_READ,
            Permission.FUNDING_SPONSOR,
            Permission.ANALYTICS_VIEW,
        }
    ),
    Role.GOV_ADMIN: frozenset(
        {
            Permission.PROBLEM_READ,
            Permission.PROBLEM_MODERATE,
            Permission.STATEMENT_PUBLISH,
            Permission.FUNDING_ALLOCATE,
            Permission.FUNDING_DISBURSE,
            Permission.ANALYTICS_VIEW_ALL,
            Permission.USER_MANAGE,
            Permission.AUDIT_READ,
        }
    ),
    Role.SUPER_ADMIN: frozenset(Permission),  # every permission
}


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def require(*permissions: Permission):  # type: ignore[no-untyped-def]
    """FastAPI dependency requiring ALL the given permissions.

    @router.post("/", dependencies=[Depends(require(Permission.STATEMENT_CREATE))])
    """

    async def _guard(
        principal: Principal = Depends(get_current_principal),
    ) -> Principal:
        missing = [p for p in permissions if not has_permission(principal.role, p)]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission(s): {', '.join(missing)}",
            )
        return principal

    return _guard


__all__ = ["ROLE_PERMISSIONS", "Permission", "Role", "has_permission", "require"]
