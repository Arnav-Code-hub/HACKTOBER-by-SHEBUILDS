"""Current profile; the caller cannot choose a UID or role."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Principal, get_current_principal
from app.modules.users.schemas import UserProfile
from app.modules.users.service import get_profile

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserProfile)
async def current_profile(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> UserProfile:
    return await get_profile(session, principal.user_id)
