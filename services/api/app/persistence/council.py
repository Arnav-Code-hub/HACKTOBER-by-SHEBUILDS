"""Cross-module authorization and transactional delivery for the external council."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError, UpstreamError
from app.core.idempotency import RequestIdentity, StoredResponse, request_hash
from app.core.roles import Role
from app.core.security import Principal
from app.integrations.council import CouncilClient
from app.modules.council.models import CouncilAssessment, TeamSupervisor
from app.modules.council.schemas import (
    AssessmentDetail,
    AssessmentList,
    AssessmentRead,
    CouncilEvidence,
    FacultyList,
    FacultyRead,
    SupervisorRead,
)
from app.modules.notifications.service import publish_case_update
from app.modules.problem_statements.models import ProblemStatement
from app.modules.projects.models import Submission
from app.modules.teams.models import Team, TeamMember
from app.modules.users.models import User
from app.persistence.idempotency import SqlIdempotencyStore
from app.persistence.participation import log, require_role, scoped_team


def read_row(row: CouncilAssessment) -> AssessmentRead:
    return AssessmentRead(
        id=row.id,
        submission_id=row.submission_id,
        title=str(row.evidence["title"]),
        status=row.status,
        completed_reviewers=row.completed_reviewers,
        created_at=row.created_at,
        error=row.error,
        supervisor_name=row.supervisor_name,
    )


def require_institute(principal: Principal) -> None:
    if principal.institute_id is None or principal.district_id is None:
        raise PermissionDeniedError("Your account has no institute/district scope.")


async def faculty_list(session: AsyncSession, principal: Principal) -> FacultyList:
    require_role(principal, Role.INSTITUTE)
    require_institute(principal)
    users = await session.scalars(
        select(User)
        .where(
            User.role == Role.FACULTY,
            User.is_active.is_(True),
            User.institute_id == principal.institute_id,
            User.district_id == principal.district_id,
        )
        .order_by(User.display_name, User.id)
    )
    return FacultyList(items=[FacultyRead(id=u.id, display_name=u.display_name) for u in users])


async def supervisor_read(
    session: AsyncSession, principal: Principal, team_id: UUID
) -> SupervisorRead:
    require_role(principal, Role.INSTITUTE, Role.STUDENT, Role.FACULTY)
    require_institute(principal)
    await scoped_team(session, principal, team_id)
    supervisor = await session.scalar(
        select(TeamSupervisor).where(TeamSupervisor.team_id == team_id)
    )
    if supervisor is None:
        return SupervisorRead(faculty_id=None, display_name=None)
    if principal.role == Role.FACULTY and supervisor.faculty_id != principal.user_id:
        raise NotFoundError("Supervision assignment not found.")
    user = await session.get(User, supervisor.faculty_id)
    return SupervisorRead(
        faculty_id=supervisor.faculty_id, display_name=user.display_name if user else None
    )


async def assign_supervisor(
    session: AsyncSession, principal: Principal, team_id: UUID, faculty_id: UUID
) -> SupervisorRead:
    require_role(principal, Role.INSTITUTE)
    require_institute(principal)
    await scoped_team(session, principal, team_id, lock=True)
    faculty = await session.scalar(
        select(User)
        .where(
            User.id == faculty_id,
            User.role == Role.FACULTY,
            User.is_active.is_(True),
            User.institute_id == principal.institute_id,
            User.district_id == principal.district_id,
        )
        .with_for_update()
    )
    if faculty is None:
        raise NotFoundError("Active faculty at your institute not found.")
    row = await session.scalar(select(TeamSupervisor).where(TeamSupervisor.team_id == team_id))
    if row is None:
        row = TeamSupervisor(team_id=team_id, faculty_id=faculty.id, assigned_by=principal.user_id)
        session.add(row)
    else:
        row.faculty_id = faculty.id
        row.assigned_by = principal.user_id
    await log(
        session,
        principal,
        "council.supervisor_assigned",
        "team",
        team_id,
        {"faculty_id": str(faculty.id)},
    )
    await session.flush()
    return SupervisorRead(faculty_id=faculty.id, display_name=faculty.display_name)


def assessment_scope(principal: Principal) -> Select[tuple[CouncilAssessment]]:
    require_role(principal, Role.STUDENT, Role.FACULTY)
    require_institute(principal)
    query = (
        select(CouncilAssessment)
        .join(Team, CouncilAssessment.team_id == Team.id)
        .join(ProblemStatement, Team.statement_id == ProblemStatement.id)
        .where(
            Team.institute_id == principal.institute_id,
            ProblemStatement.district_id == principal.district_id,
        )
    )
    if principal.role == Role.FACULTY:
        return query.where(CouncilAssessment.supervisor_id == principal.user_id)
    return query.where(
        select(TeamMember.id)
        .where(TeamMember.team_id == Team.id, TeamMember.user_id == principal.user_id)
        .exists()
    )


async def assessment_get(
    session: AsyncSession,
    principal: Principal,
    identity: UUID,
    *,
    lock: bool = False,
    with_pdf: bool = False,
) -> CouncilAssessment:
    query = assessment_scope(principal).where(CouncilAssessment.id == identity)
    if not with_pdf:
        query = query.options(defer(CouncilAssessment.pdf))
    if lock:
        query = query.with_for_update(of=CouncilAssessment)
    row = await session.scalar(query)
    if row is None:
        raise NotFoundError("Council assessment not found.")
    return row


async def assessment_list(session: AsyncSession, principal: Principal) -> AssessmentList:
    result = await session.execute(
        assessment_scope(principal)
        .with_only_columns(
            CouncilAssessment.id,
            CouncilAssessment.submission_id,
            CouncilAssessment.evidence["title"].as_string().label("title"),
            CouncilAssessment.status,
            CouncilAssessment.completed_reviewers,
            CouncilAssessment.created_at,
            CouncilAssessment.error,
            CouncilAssessment.supervisor_name,
            maintain_column_froms=True,
        )
        .order_by(CouncilAssessment.created_at.desc(), CouncilAssessment.id)
        .limit(100)
    )
    return AssessmentList(items=[AssessmentRead.model_validate(r) for r in result.mappings()])


async def assessment_detail(
    session: AsyncSession, principal: Principal, identity: UUID
) -> AssessmentDetail:
    row = await assessment_get(session, principal, identity)
    return AssessmentDetail(
        **read_row(row).model_dump(),
        report=row.report if row.status == "available" else None,
        evidence=CouncilEvidence.model_validate(row.evidence),
    )


async def create_assessment(
    session: AsyncSession,
    principal: Principal,
    submission_id: UUID,
    body: CouncilEvidence,
    key: str,
) -> StoredResponse:
    require_role(principal, Role.STUDENT)
    require_institute(principal)

    async def action() -> StoredResponse:
        submission = await session.get(Submission, submission_id)
        if submission is None:
            raise NotFoundError("Submission not found.")
        team = await scoped_team(session, principal, submission.team_id, lock=True)
        if not team.institute_approved:
            raise ConflictError("The institute must approve your team before council assessment.")
        assignment = await session.scalar(
            select(TeamSupervisor).where(TeamSupervisor.team_id == team.id)
        )
        if assignment is None:
            raise ConflictError("The institute must assign a supervising faculty member first.")
        faculty = await session.scalar(
            select(User)
            .where(
                User.id == assignment.faculty_id,
                User.role == Role.FACULTY,
                User.is_active.is_(True),
                User.institute_id == principal.institute_id,
                User.district_id == principal.district_id,
            )
            .with_for_update()
        )
        if faculty is None:
            raise ConflictError(
                "The assigned supervisor is unavailable; ask your institute to reassign."
            )
        row = CouncilAssessment(
            submission_id=submission.id,
            team_id=team.id,
            supervisor_id=faculty.id,
            supervisor_name=faculty.display_name,
            requested_by=principal.user_id,
            request_key=key,
            evidence=body.model_dump(mode="json"),
            status="queued",
            completed_reviewers=0,
            retry_requested=False,
            next_attempt_at=datetime.now(UTC),
        )
        session.add(row)
        await session.flush()
        await session.refresh(row)
        await log(
            session,
            principal,
            "council.requested",
            "council_assessment",
            row.id,
            {"submission_id": str(submission.id), "supervisor_id": str(faculty.id)},
        )
        return StoredResponse(202, read_row(row).model_dump(mode="json"))

    return await SqlIdempotencyStore().execute(
        session,
        RequestIdentity(
            principal.user_id,
            "council.assess",
            key,
            request_hash(
                {"submission_id": str(submission_id), "evidence": body.model_dump(mode="json")}
            ),
        ),
        action,
    )


async def request_retry(
    session: AsyncSession, principal: Principal, identity: UUID
) -> AssessmentRead:
    require_role(principal, Role.STUDENT)
    row = await assessment_get(session, principal, identity, lock=True)
    if row.status not in {"incomplete", "delivery_failed"}:
        raise ConflictError("Only an incomplete or failed delivery can be retried.")
    if row.status == "incomplete":
        row.retry_requested = True
        row.retry_key = str(uuid4())
    row.status = "queued" if row.remote_id is None else "reviewing"
    row.error = None
    row.next_attempt_at = datetime.now(UTC)
    await log(session, principal, "council.retry_requested", "council_assessment", row.id, {})
    return read_row(row)


def validate_remote(evidence: CouncilEvidence, remote: Any, allow_simulation: bool) -> None:
    if remote.project != evidence:
        raise UpstreamError("Council evidence snapshot does not match the submitted evidence.")
    if remote.status == "completed":
        if remote.completed_reviewers != 5 or remote.report is None:
            raise UpstreamError("Council returned an incomplete report as completed.")
        if remote.report.simulated and not allow_simulation:
            raise UpstreamError("Simulated council output cannot be published in live integration.")
        sizes = {
            f"E{i:02}": len(value.splitlines()) or 1
            for i, value in enumerate(
                [
                    evidence.research_question,
                    evidence.findings,
                    evidence.methods,
                    evidence.results,
                    evidence.limitations,
                ]
                + [f.content for f in evidence.files],
                1,
            )
        }
        for review in remote.report.reviewers:
            for item in [*review.strengths, *review.issues]:
                for ref in item.evidence:
                    if not 1 <= ref.start_line <= ref.end_line <= sizes.get(ref.evidence_id, 0):
                        raise UpstreamError(
                            "Council report contains an invalid evidence reference."
                        )


async def advance(
    session: AsyncSession, row: CouncilAssessment, client: CouncilClient, settings: Settings
) -> None:
    """Caller holds a row lock; upstream uses the durable local ID as its retry key."""
    now = datetime.now(UTC)
    try:
        evidence = CouncilEvidence.model_validate(row.evidence)
        if row.remote_id is None:
            row.remote_id = await client.submit(str(row.id), evidence)
        if row.retry_requested:
            if not row.retry_key:
                raise UpstreamError("Council retry identity is missing; request a new retry.")
            await client.retry(row.remote_id, row.retry_key)
            row.retry_requested = False
        remote = await client.read(row.remote_id)
        if remote.id != row.remote_id:
            raise UpstreamError("Council returned the wrong assessment identity.")
        validate_remote(evidence, remote, settings.council_allow_simulation)
        row.completed_reviewers = remote.completed_reviewers
        row.error = None
        if remote.status == "completed":
            assert remote.report is not None
            pdf = await client.pdf(row.remote_id)
            # Store report and artifact atomically; available means both are durable in JanMaang.
            row.report = remote.report.model_dump(mode="json")
            row.pdf = pdf
            row.status = "available"
            row.delivered_at = now
            members = list(
                await session.scalars(
                    select(TeamMember.user_id)
                    .join(User, User.id == TeamMember.user_id)
                    .where(
                        TeamMember.team_id == row.team_id,
                        User.is_active.is_(True),
                        User.role == Role.STUDENT,
                    )
                )
            )
            await publish_case_update(
                session,
                [row.supervisor_id, *members],
                event_key="council.completed",
                title="AI Council report available",
                body="The project's advisory report and PDF are ready in your council workspace.",
                resource_type="council_assessment",
                resource_id=row.id,
            )
        elif remote.status == "incomplete":
            row.status = "incomplete"
            row.error = "Council assessment is incomplete. No completed report has been published."
        else:
            row.status = "reviewing"
        row.next_attempt_at = now + timedelta(seconds=10)
    except UpstreamError as exc:
        row.status = "delivery_failed"
        row.error = exc.detail
        row.next_attempt_at = now + timedelta(seconds=60)
