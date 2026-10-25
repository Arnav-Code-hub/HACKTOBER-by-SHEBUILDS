"""Phase 0 startup, request hashing, lifecycle and record-scope guarantees."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError as SettingsError

from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from app.core.idempotency import RequestIdentity, request_hash
from app.core.lifecycle import ALLOWED, StatusSnapshot, effective_status, validate_transition
from app.core.permissions import Permission, has_permission
from app.core.roles import Role
from app.core.scope import require_assignment, require_department, require_institute, require_owner
from app.core.security import Principal
from app.shared.enums import ProblemStatus as Status


def test_staging_needs_no_redis() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://test:test@localhost/test",
        environment="staging",
        cors_origins="http://localhost:3000,http://127.0.0.1:8080",
    )
    assert settings.redis_url is None
    assert settings.cors_origins == ["http://localhost:3000", "http://127.0.0.1:8080"]
    assert settings.gemini_timeout_seconds == 8
    assert not hasattr(settings, "auth_secret")
    assert not hasattr(settings, "access_token_ttl_minutes")


@pytest.mark.parametrize("origin", ["*", "https://site.test/path", "https://user:pass@site.test"])
def test_cors_refuses_non_origins(origin: str) -> None:
    with pytest.raises(SettingsError):
        Settings(_env_file=None, cors_origins=origin)


def test_demo_is_not_a_runtime_environment() -> None:
    with pytest.raises(SettingsError):
        Settings(_env_file=None, environment="demo")


def test_hash_is_canonical_and_payload_sensitive() -> None:
    assert request_hash({"a": 1, "nested": {"x": 2, "y": 3}}) == request_hash(
        {"nested": {"y": 3, "x": 2}, "a": 1}
    )
    assert request_hash({"amount": 1}) != request_hash({"amount": 2})
    assert request_hash({"photos": [1, 2]}) != request_hash({"photos": [2, 1]})


def test_hash_rejects_non_json_numbers() -> None:
    with pytest.raises(ValueError):
        request_hash({"amount": float("nan")})


def test_identity_requires_an_operation_and_a_bounded_key() -> None:
    with pytest.raises(ValueError):
        RequestIdentity(uuid4(), "reports:create", "", "hash")


def test_cluster_is_the_only_execution_status() -> None:
    report = StatusSnapshot(Status.VERIFIED, datetime(2026, 10, 1, tzinfo=UTC))
    cluster = StatusSnapshot(Status.AWAITING_VERIFICATION, datetime(2026, 10, 24, tzinfo=UTC))
    assert effective_status(report) == report
    assert effective_status(report, cluster) == cluster
    with pytest.raises(ValueError):
        effective_status(cluster)


def test_all_allowed_transitions_have_a_permission() -> None:
    assert len(ALLOWED) == 8
    assert all(ALLOWED.values())
    assert (Status.CITIZEN_VERIFIED, Status.IN_PROGRESS) not in ALLOWED


@pytest.mark.parametrize(
    ("from_", "to", "role"),
    [
        (Status.REPORTED, Status.VERIFIED, Role.PANCHAYAT),
        (Status.REPORTED, Status.REJECTED, Role.PANCHAYAT),
        (Status.VERIFIED, Status.PRIORITISED, Role.PANCHAYAT),
        (Status.PRIORITISED, Status.FUNDED, Role.DEPARTMENT),
        (Status.FUNDED, Status.IN_PROGRESS, Role.OFFICER),
        (Status.IN_PROGRESS, Status.AWAITING_VERIFICATION, Role.OFFICER),
        (Status.AWAITING_VERIFICATION, Status.CITIZEN_VERIFIED, Role.CITIZEN),
        (Status.AWAITING_VERIFICATION, Status.IN_PROGRESS, Role.CITIZEN),
    ],
)
def test_every_agreed_transition_has_an_authorized_actor(
    principals: dict[Role, Principal], from_: Status, to: Status, role: Role
) -> None:
    validate_transition(
        from_,
        to,
        actor=principals[role],
        reason="Checked locally",
        current_round=1,
        expected_round=1,
    )


def test_transition_permissions_and_rejection_reason(principals: dict[Role, Principal]) -> None:
    with pytest.raises(PermissionDeniedError):
        validate_transition(Status.PRIORITISED, Status.FUNDED, actor=principals[Role.CITIZEN])
    with pytest.raises(ValidationError):
        validate_transition(Status.REPORTED, Status.REJECTED, actor=principals[Role.PANCHAYAT])
    validate_transition(
        Status.REPORTED, Status.REJECTED, actor=principals[Role.PANCHAYAT], reason="Duplicate"
    )
    with pytest.raises(ConflictError):
        validate_transition(Status.REPORTED, Status.FUNDED, actor=principals[Role.DEPARTMENT])


@pytest.mark.parametrize("expected", [None, 1, 3])
def test_stale_verification_is_not_a_transition(
    principals: dict[Role, Principal], expected: int | None
) -> None:
    with pytest.raises(ConflictError):
        validate_transition(
            Status.AWAITING_VERIFICATION,
            Status.CITIZEN_VERIFIED,
            actor=principals[Role.CITIZEN],
            current_round=2,
            expected_round=expected,
        )


def test_staff_cannot_citizen_verify() -> None:
    assert not has_permission(Role.PANCHAYAT, Permission.PROBLEM_VERIFY)
    assert not has_permission(Role.OFFICER, Permission.PROBLEM_VERIFY)
    assert has_permission(Role.INSTITUTE, Permission.PROJECT_APPROVE)
    assert has_permission(Role.DEPARTMENT, Permission.WORKORDER_ASSIGN)
    assert has_permission(Role.OFFICER, Permission.WORKORDER_UPDATE)
    for role in (Role.STUDENT, Role.FACULTY, Role.INSTITUTE, Role.INDUSTRY):
        assert has_permission(role, Permission.STATEMENT_READ_PUBLISHED)


def test_district_department_assignment_and_institute_checks(
    principals: dict[Role, Principal],
) -> None:
    officer = principals[Role.OFFICER]
    assert officer.district_id and officer.department_id and officer.institute_id
    require_assignment(officer, officer.district_id, officer.department_id, officer.user_id)
    with pytest.raises(NotFoundError):
        require_assignment(officer, officer.district_id, officer.department_id, uuid4())
    with pytest.raises(NotFoundError):
        require_department(officer, uuid4(), officer.department_id)
    with pytest.raises(NotFoundError):
        require_department(officer, officer.district_id, uuid4())
    with pytest.raises(NotFoundError):
        require_institute(officer, uuid4())
    with pytest.raises(NotFoundError):
        require_owner(principals[Role.SUPER_ADMIN], officer.user_id)
