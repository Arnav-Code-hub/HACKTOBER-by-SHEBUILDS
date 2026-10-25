"""Provisioned database profiles, never client-supplied role claims."""

from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, PermissionDeniedError
from app.core.roles import Role
from app.modules.departments.service import validate_active_scope
from app.modules.users.models import User
from app.modules.users.schemas import OfficerList, OfficerSummary, UserProfile


async def _profile(session: AsyncSession, user: User | None) -> UserProfile:
    if user is None or not user.is_active:
        raise PermissionDeniedError("This account is not provisioned or is disabled.")
    return await _scoped(session, user)


async def _scoped(session: AsyncSession, user: User) -> UserProfile:
    """The role's required scope is present, active and inside the district."""
    profile = UserProfile.model_validate(user)
    if profile.role != Role.SUPER_ADMIN and profile.district_id is None:
        raise PermissionDeniedError("Your account has no assigned district.")
    if profile.role in {Role.OFFICER, Role.DEPARTMENT} and profile.department_id is None:
        raise PermissionDeniedError("Your account has no assigned department.")
    if (
        profile.role in {Role.STUDENT, Role.FACULTY, Role.INSTITUTE}
        and profile.institute_id is None
    ):
        raise PermissionDeniedError("Your account has no assigned institute.")
    if profile.role == Role.INDUSTRY and profile.organization_id is None:
        raise PermissionDeniedError("Your account has no assigned organization.")
    await validate_active_scope(
        session,
        profile.district_id,
        {
            "department": profile.department_id,
            "institute": profile.institute_id,
            "industry": profile.organization_id,
        },
    )
    return profile


async def profile_by_uid(session: AsyncSession, uid: str) -> UserProfile:
    user = await session.scalar(select(User).where(User.firebase_uid == uid))
    return await _profile(session, user)


async def get_profile(session: AsyncSession, user_id: UUID) -> UserProfile:
    return await _profile(session, await session.get(User, user_id))


async def validate_scope(session: AsyncSession, user_id: UUID) -> None:
    """Check a user's role and scope fit, whether or not the account is active.

    Administrators may correct a disabled account's scope; signing in still
    requires an active account.
    """
    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    await _scoped(session, user)


def _officers(district_id: UUID, department_id: UUID) -> Select[tuple[User]]:
    return select(User).where(
        User.role == Role.OFFICER,
        User.is_active.is_(True),
        User.district_id == district_id,
        User.department_id == department_id,
    )


async def assignable_officers(
    session: AsyncSession, district_id: UUID, department_id: UUID
) -> OfficerList:
    """Active officers in exactly this district and department."""
    officers = (
        await session.scalars(
            _officers(district_id, department_id).order_by(User.display_name, User.id)
        )
    ).all()
    return OfficerList(
        items=[
            OfficerSummary(id=o.id, display_name=o.display_name, email=o.email) for o in officers
        ]
    )


async def is_assignable_officer(
    session: AsyncSession, officer_id: UUID, district_id: UUID, department_id: UUID
) -> bool:
    """Check and share-lock the officer until the caller's transaction ends.

    An administrator's role or scope change locks the same row for update, so
    it either sees the new assignment and refuses, or commits first and this
    check fails.
    """
    found = await session.scalar(
        _officers(district_id, department_id)
        .where(User.id == officer_id)
        .with_for_update(read=True)
    )
    return found is not None
