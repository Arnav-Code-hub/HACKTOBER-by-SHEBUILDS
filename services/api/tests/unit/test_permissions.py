"""Permission matrix tests.

Nine web roles times twenty-odd permissions is the largest silent-failure surface
in the platform, so the matrix is asserted directly rather than exercised
incidentally through endpoints.
"""

from app.core.permissions import ROLE_PERMISSIONS, Permission, Role, has_permission


def test_every_role_has_an_entry() -> None:
    assert set(ROLE_PERMISSIONS) == set(Role)


def test_super_admin_has_every_permission() -> None:
    assert ROLE_PERMISSIONS[Role.SUPER_ADMIN] == frozenset(Permission)


def test_citizen_cannot_allocate_funding() -> None:
    assert not has_permission(Role.CITIZEN, Permission.FUNDING_ALLOCATE)


def test_student_cannot_publish_problem_statements() -> None:
    assert not has_permission(Role.STUDENT, Permission.STATEMENT_PUBLISH)


def test_only_privileged_roles_read_the_audit_log() -> None:
    allowed = {r for r in Role if has_permission(r, Permission.AUDIT_READ)}
    assert allowed == {Role.GOV_ADMIN, Role.SUPER_ADMIN}
