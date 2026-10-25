"""Authentication: Firebase ID token in, local Principal out.

Firebase Auth stays the identity provider — phone OTP for rural citizens is
genuinely hard to replace and carries no demo value. Everything downstream of
this module deals only in `Principal`, so swapping the provider later touches
one file.
"""

from dataclasses import dataclass
from typing import Protocol, cast
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.roles import Role

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class Principal:
    """The authenticated caller. Never a Firebase object — always ours."""

    user_id: UUID
    firebase_uid: str
    role: Role
    district_id: UUID | None = None
    department_id: UUID | None = None
    institute_id: UUID | None = None
    organization_id: UUID | None = None
    is_demo: bool = False


class Authenticator(Protocol):
    async def resolve(self, token: str, session: AsyncSession) -> Principal: ...


async def get_current_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> Principal:
    """Verify the bearer token and resolve it to a local user.

    The application composition root supplies provider verification and local
    profile resolution. Core does not import business modules.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    authenticator = cast(Authenticator, request.app.state.authenticator)
    return await authenticator.resolve(credentials.credentials, session)
