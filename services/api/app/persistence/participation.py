"""Transactional adapter joining partner records across module boundaries.

All writes use the caller's transaction. Row locks serialize approval and
submission eligibility, and duplicate reviews, independently of retry keys.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditEvent
from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError
from app.core.idempotency import RequestIdentity, StoredResponse, request_hash
from app.core.roles import Role
from app.core.security import Principal
from app.modules.funding.models import Sponsorship
from app.modules.funding.pledge_schemas import PledgeCreate, PledgeList, PledgeRead
from app.modules.problem_statements.models import ProblemStatement
from app.modules.projects.models import Review, Submission
from app.modules.projects.schemas import (
    ReviewCreate,
    ReviewRead,
    SubmissionCreate,
    SubmissionList,
    SubmissionRead,
)
from app.modules.teams.models import Team, TeamMember
from app.modules.teams.schemas import TeamCreate, TeamList, TeamRead
from app.persistence.audit import SqlAuditWriter
from app.persistence.idempotency import SqlIdempotencyStore


def require_role(principal: Principal, *roles: Role) -> None:
    if principal.role not in roles or principal.district_id is None:
        raise PermissionDeniedError("This account cannot perform this action.")


async def published(
    session: AsyncSession, principal: Principal, identity: UUID
) -> ProblemStatement:
    statement = await session.scalar(
        select(ProblemStatement).where(
            ProblemStatement.id == identity,
            ProblemStatement.district_id == principal.district_id,
            ProblemStatement.status == "published",
        )
    )
    if statement is None:
        raise NotFoundError("Published statement not found.")
    return statement


async def log(
    session: AsyncSession,
    principal: Principal,
    action: str,
    kind: str,
    identity: UUID,
    after: dict[str, object],
) -> None:
    await SqlAuditWriter().log_event(
        session,
        AuditEvent(
            principal.user_id,
            action,
            kind,
            identity,
            principal.district_id,
            after=after,
        ),
    )


def team_query() -> Select[tuple[Team, str, int]]:
    members = (
        select(func.count())
        .select_from(TeamMember)
        .where(TeamMember.team_id == Team.id)
        .correlate(Team)
        .scalar_subquery()
    )
    return select(Team, ProblemStatement.title, members).join(
        ProblemStatement, Team.statement_id == ProblemStatement.id
    )


def team_result(team: Team, title: str, members: int) -> TeamRead:
    return TeamRead(
        id=team.id,
        name=team.name,
        statement_id=team.statement_id,
        statement_title=title,
        institute_approved=team.institute_approved,
        member_count=members,
        created_at=team.created_at,
    )


async def team_read(session: AsyncSession, team: Team) -> TeamRead:
    row = (await session.execute(team_query().where(Team.id == team.id))).one()
    return team_result(*row)


async def scoped_team(
    session: AsyncSession, principal: Principal, identity: UUID, *, lock: bool = False
) -> Team:
    query = (
        select(Team)
        .join(ProblemStatement, Team.statement_id == ProblemStatement.id)
        .where(
            Team.id == identity,
            Team.institute_id == principal.institute_id,
            ProblemStatement.district_id == principal.district_id,
        )
    )
    if principal.role == Role.STUDENT:
        query = query.where(
            select(TeamMember.id)
            .where(TeamMember.team_id == Team.id, TeamMember.user_id == principal.user_id)
            .exists()
        )
    if lock:
        query = query.with_for_update(of=Team).execution_options(populate_existing=True)
    team = await session.scalar(query)
    if team is None:
        raise NotFoundError("Team not found.")
    return team


def list_scope(principal: Principal, mine: bool, institute: str | None) -> None:
    require_role(principal, Role.STUDENT, Role.FACULTY, Role.INSTITUTE)
    if principal.institute_id is None:
        raise PermissionDeniedError("Your account has no institute.")
    if (principal.role == Role.STUDENT and (not mine or institute is not None)) or (
        principal.role != Role.STUDENT and (mine or institute != "me")
    ):
        raise PermissionDeniedError("Use your assigned team or institute scope.")


async def list_teams(
    session: AsyncSession, principal: Principal, mine: bool, institute: str | None
) -> TeamList:
    list_scope(principal, mine, institute)
    query = team_query().where(
        Team.institute_id == principal.institute_id,
        ProblemStatement.district_id == principal.district_id,
    )
    if mine:
        query = query.where(
            select(TeamMember.id)
            .where(TeamMember.team_id == Team.id, TeamMember.user_id == principal.user_id)
            .exists()
        )
    rows = (await session.execute(query.order_by(Team.created_at.desc(), Team.id))).all()
    return TeamList(items=[team_result(*row) for row in rows])


async def create_team(
    session: AsyncSession, principal: Principal, body: TeamCreate, key: str
) -> StoredResponse:
    require_role(principal, Role.STUDENT)
    if principal.institute_id is None:
        raise PermissionDeniedError("Your account has no institute.")

    async def action() -> StoredResponse:
        await published(session, principal, body.statement_id)
        team = Team(
            name=body.name,
            statement_id=body.statement_id,
            institute_id=principal.institute_id,
            created_by=principal.user_id,
            institute_approved=False,
            is_demo=principal.is_demo,
        )
        session.add(team)
        await session.flush()
        session.add(
            TeamMember(team_id=team.id, user_id=principal.user_id, is_demo=principal.is_demo)
        )
        await session.flush()
        await log(
            session,
            principal,
            "team.created",
            "team",
            team.id,
            {"name": team.name, "statement_id": str(team.statement_id)},
        )
        return StoredResponse(201, (await team_read(session, team)).model_dump(mode="json"))

    return await SqlIdempotencyStore().execute(
        session,
        RequestIdentity(
            principal.user_id, "teams.create", key, request_hash(body.model_dump(mode="json"))
        ),
        action,
    )


async def approve_team(session: AsyncSession, principal: Principal, identity: UUID) -> TeamRead:
    require_role(principal, Role.INSTITUTE)
    team = await scoped_team(session, principal, identity, lock=True)
    await published(session, principal, team.statement_id)
    if not team.institute_approved:
        team.institute_approved = True
        team.approved_by = principal.user_id
        team.approved_at = datetime.now(UTC)
        await log(
            session, principal, "team.approved", "team", team.id, {"institute_approved": True}
        )
    return await team_read(session, team)


def submission_query(principal: Principal) -> Select[tuple[Submission, str, str, int, int, str]]:
    count = (
        select(func.count())
        .select_from(Review)
        .where(Review.submission_id == Submission.id)
        .correlate(Submission)
        .scalar_subquery()
    )
    return (
        select(Submission, Team.name, ProblemStatement.title, count, Review.score, Review.comment)
        .join(Team, Submission.team_id == Team.id)
        .join(ProblemStatement, Submission.statement_id == ProblemStatement.id)
        .outerjoin(
            Review,
            (Review.submission_id == Submission.id) & (Review.reviewer_id == principal.user_id),
        )
    )


def submission_result(
    submission: Submission,
    team_name: str,
    statement_title: str,
    count: int,
    score: int | None,
    comment: str | None,
) -> SubmissionRead:
    return SubmissionRead(
        id=submission.id,
        team_id=submission.team_id,
        team_name=team_name,
        statement_title=statement_title,
        title=submission.title,
        summary=submission.summary,
        link=submission.link,
        submitted_at=submission.submitted_at,
        review_count=count,
        my_review=ReviewRead(score=score, comment=comment or "") if score is not None else None,
    )


async def submission_read(
    session: AsyncSession, principal: Principal, submission: Submission
) -> SubmissionRead:
    row = (
        await session.execute(submission_query(principal).where(Submission.id == submission.id))
    ).one()
    return submission_result(*row)


async def list_submissions(
    session: AsyncSession, principal: Principal, mine: bool, institute: str | None
) -> SubmissionList:
    list_scope(principal, mine, institute)
    query = submission_query(principal).where(
        Team.institute_id == principal.institute_id,
        ProblemStatement.district_id == principal.district_id,
    )
    if mine:
        query = query.where(
            select(TeamMember.id)
            .where(TeamMember.team_id == Team.id, TeamMember.user_id == principal.user_id)
            .exists()
        )
    rows = (
        await session.execute(query.order_by(Submission.submitted_at.desc(), Submission.id))
    ).all()
    return SubmissionList(items=[submission_result(*row) for row in rows])


async def create_submission(
    session: AsyncSession, principal: Principal, body: SubmissionCreate, key: str
) -> StoredResponse:
    require_role(principal, Role.STUDENT)

    async def action() -> StoredResponse:
        team = await scoped_team(session, principal, body.team_id, lock=True)
        await published(session, principal, team.statement_id)
        if not team.institute_approved:
            raise ConflictError("Your institute must approve the team before submission.")
        submission = Submission(
            team_id=team.id,
            statement_id=team.statement_id,
            submitted_by=principal.user_id,
            title=body.title,
            summary=body.summary,
            link=body.link,
            is_demo=principal.is_demo,
        )
        session.add(submission)
        await session.flush()
        await log(
            session,
            principal,
            "submission.created",
            "submission",
            submission.id,
            {"team_id": str(team.id), "title": submission.title},
        )
        return StoredResponse(
            201, (await submission_read(session, principal, submission)).model_dump(mode="json")
        )

    return await SqlIdempotencyStore().execute(
        session,
        RequestIdentity(
            principal.user_id, "submissions.create", key, request_hash(body.model_dump(mode="json"))
        ),
        action,
    )


async def review_submission(
    session: AsyncSession, principal: Principal, identity: UUID, body: ReviewCreate, key: str
) -> StoredResponse:
    require_role(principal, Role.FACULTY)

    async def action() -> StoredResponse:
        submission = await session.scalar(
            select(Submission)
            .where(Submission.id == identity)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if submission is None:
            raise NotFoundError("Submission not found.")
        team = await scoped_team(session, principal, submission.team_id, lock=True)
        await published(session, principal, team.statement_id)
        if not team.institute_approved:
            raise ConflictError("Only an approved team's submission can be reviewed.")
        if await session.scalar(
            select(Review.id).where(
                Review.submission_id == identity, Review.reviewer_id == principal.user_id
            )
        ):
            raise ConflictError("You have already reviewed this submission.")
        review = Review(
            submission_id=identity,
            reviewer_id=principal.user_id,
            score=body.score,
            comment=body.comment,
            is_demo=principal.is_demo,
        )
        session.add(review)
        await session.flush()
        await log(
            session,
            principal,
            "submission.reviewed",
            "submission",
            identity,
            {"review_id": str(review.id), "score": review.score},
        )
        return StoredResponse(201, {"id": str(review.id)})

    return await SqlIdempotencyStore().execute(
        session,
        RequestIdentity(
            principal.user_id,
            "submissions.review",
            key,
            request_hash({"id": str(identity), **body.model_dump(mode="json")}),
        ),
        action,
    )


def pledge_result(pledge: Sponsorship, title: str) -> PledgeRead:
    return PledgeRead(
        id=pledge.id,
        statement_id=pledge.statement_id,
        statement_title=title,
        amount_paise=pledge.amount_paise,
        status="pledged",
        pledged_at=pledge.pledged_at,
    )


async def pledge_read(session: AsyncSession, pledge: Sponsorship) -> PledgeRead:
    title = await session.scalar(
        select(ProblemStatement.title).where(ProblemStatement.id == pledge.statement_id)
    )
    assert title is not None
    return pledge_result(pledge, title)


async def list_pledges(session: AsyncSession, principal: Principal, mine: bool) -> PledgeList:
    require_role(principal, Role.INDUSTRY)
    if not mine:
        raise PermissionDeniedError("Use your own sponsorship scope.")
    rows = (
        await session.execute(
            select(Sponsorship, ProblemStatement.title)
            .join(ProblemStatement, Sponsorship.statement_id == ProblemStatement.id)
            .where(
                Sponsorship.pledged_by == principal.user_id,
                Sponsorship.organization_id == principal.organization_id,
                ProblemStatement.district_id == principal.district_id,
            )
            .order_by(Sponsorship.pledged_at.desc(), Sponsorship.id)
        )
    ).all()
    return PledgeList(items=[pledge_result(*row) for row in rows])


async def create_pledge(
    session: AsyncSession, principal: Principal, identity: UUID, body: PledgeCreate, key: str
) -> StoredResponse:
    require_role(principal, Role.INDUSTRY)
    if principal.organization_id is None:
        raise PermissionDeniedError("Your account has no industry organization.")

    async def action() -> StoredResponse:
        await published(session, principal, identity)
        pledge = Sponsorship(
            statement_id=identity,
            organization_id=principal.organization_id,
            pledged_by=principal.user_id,
            amount_paise=body.amount_paise,
            status="pledged",
            is_demo=principal.is_demo,
        )
        session.add(pledge)
        await session.flush()
        await log(
            session,
            principal,
            "sponsorship.pledged",
            "sponsorship",
            pledge.id,
            {
                "statement_id": str(identity),
                "amount_paise": pledge.amount_paise,
                "status": "pledged",
            },
        )
        return StoredResponse(201, (await pledge_read(session, pledge)).model_dump(mode="json"))

    return await SqlIdempotencyStore().execute(
        session,
        RequestIdentity(
            principal.user_id,
            "sponsorships.create",
            key,
            request_hash({"id": str(identity), **body.model_dump(mode="json")}),
        ),
        action,
    )
