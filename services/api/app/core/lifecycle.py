"""One lifecycle definition and the transaction adapter contract for Phase 1."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, PermissionDeniedError, ValidationError
from app.core.permissions import Permission, has_permission
from app.core.security import Principal
from app.shared.enums import ProblemStatus as Status

ALLOWED: dict[tuple[Status, Status], frozenset[Permission]] = {
    (Status.REPORTED, Status.VERIFIED): frozenset({Permission.PROBLEM_MODERATE}),
    (Status.REPORTED, Status.REJECTED): frozenset({Permission.PROBLEM_MODERATE}),
    (Status.VERIFIED, Status.PRIORITISED): frozenset({Permission.CLUSTER_CONFIRM}),
    (Status.PRIORITISED, Status.FUNDED): frozenset(
        {Permission.FUNDING_ALLOCATE, Permission.WORKORDER_ASSIGN}
    ),
    (Status.FUNDED, Status.IN_PROGRESS): frozenset({Permission.WORKORDER_UPDATE}),
    (Status.IN_PROGRESS, Status.AWAITING_VERIFICATION): frozenset({Permission.WORKORDER_UPDATE}),
    (Status.AWAITING_VERIFICATION, Status.CITIZEN_VERIFIED): frozenset({Permission.PROBLEM_VERIFY}),
    (Status.AWAITING_VERIFICATION, Status.IN_PROGRESS): frozenset({Permission.PROBLEM_VERIFY}),
}

REPORT_STATUSES = frozenset({Status.REPORTED, Status.VERIFIED, Status.REJECTED})

# A report may join an existing cluster only before its repair is submitted
# for citizen verification. Joining a cluster that awaits or has passed
# verification would display the new complaint as already fixed and hide a
# recurrence; the Panchayat starts a new cluster instead.
JOINABLE_CLUSTER_STATUSES = frozenset({Status.PRIORITISED, Status.FUNDED, Status.IN_PROGRESS})


@dataclass(frozen=True)
class StatusSnapshot:
    status: Status
    status_changed_at: datetime | None


def effective_status(
    report_status: StatusSnapshot, cluster_status: StatusSnapshot | None = None
) -> StatusSnapshot:
    """A clustered report and its work order expose the cluster's one status."""
    if cluster_status is not None:
        if cluster_status.status in REPORT_STATUSES:
            raise ValueError("A cluster must use an execution status")
        return cluster_status
    if report_status.status not in REPORT_STATUSES:
        raise ValueError("An unclustered report must use a report status")
    return report_status


def require_transition_permission(from_: Status, to: Status, actor: Principal) -> None:
    permissions = ALLOWED.get((from_, to))
    if permissions is None:
        raise ConflictError("The record is no longer in the required state.")
    if not all(has_permission(actor.role, p) for p in permissions):
        raise PermissionDeniedError("Your account cannot make this change.")


def validate_transition(
    from_: Status,
    to: Status,
    *,
    actor: Principal,
    reason: str | None = None,
    current_round: int | None = None,
    expected_round: int | None = None,
) -> None:
    require_transition_permission(from_, to, actor)
    if to == Status.REJECTED and not (reason and reason.strip()):
        raise ValidationError("A rejection reason is required.")
    if from_ == Status.AWAITING_VERIFICATION and (
        current_round is None or expected_round is None or current_round != expected_round
    ):
        raise ConflictError("This repair was updated; reload the latest evidence.")


class TransitionStore(Protocol):
    async def transition(
        self,
        session: AsyncSession,
        record_id: UUID,
        from_: Status,
        to: Status,
        *,
        actor: Principal,
        reason: str | None,
        expected_round: int | None = None,
        comment: str | None = None,
    ) -> StatusSnapshot:
        """Phase 1: check scope/ownership, CAS or lock, timestamp and audit.

        A citizen verdict (from awaiting_verification) also records its
        verification row for the reviewed round, with ``comment``, before
        a negative verdict advances the round. Callers never insert it.

        Compare the round while holding the work-order lock. The cluster is
        the execution status owner; a work order has no separate status.
        Never commit this caller-owned transaction here.
        """
        ...
