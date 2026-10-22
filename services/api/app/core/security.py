"""Authentication: Firebase ID token in, local Principal out.

Firebase Auth stays the identity provider — phone OTP for rural citizens is
genuinely hard to replace and carries no demo value. Everything downstream of
this module deals only in `Principal`, so swapping the provider later touches
one file.
"""

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

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


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Principal:
    """Verify the bearer token and resolve it to a local user.

    TODO(auth): verify with firebase_admin.auth.verify_id_token, then look the
    firebase_uid up in the users table. Until the auth module lands this raises,
    so no endpoint can accidentally ship unauthenticated.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    raise NotImplementedError("Implement in app/modules/auth/service.py")
