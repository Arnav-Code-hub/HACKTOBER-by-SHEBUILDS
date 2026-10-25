"""Verify the provider identity, then resolve permissions from the database."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Principal
from app.integrations.firebase import TokenVerifier
from app.modules.users.service import profile_by_uid


class DatabaseAuthenticator:
    def __init__(self, verifier: TokenVerifier) -> None:
        self.verifier = verifier

    async def resolve(self, token: str, session: AsyncSession) -> Principal:
        uid = await self.verifier.verify(token)
        profile = await profile_by_uid(session, uid)
        return Principal(
            user_id=profile.id,
            firebase_uid=profile.firebase_uid,
            role=profile.role,
            district_id=profile.district_id,
            department_id=profile.department_id,
            institute_id=profile.institute_id,
            organization_id=profile.organization_id,
            is_demo=profile.is_demo,
        )
