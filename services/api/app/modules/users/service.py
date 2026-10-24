"""Provisioned database profiles, never client-supplied role claims."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import PermissionDeniedError
from app.core.roles import Role
from app.modules.departments.service import validate_active_scope
from app.modules.users.models import User
from app.modules.users.schemas import UserProfile


async def _profile(session: AsyncSession, user: User | None) -> UserProfile:
    if user is None or not user.is_active:
        raise PermissionDeniedError("This account is not provisioned or is disabled.")
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
