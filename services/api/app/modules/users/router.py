"""Current profile; the caller cannot choose a UID or role."""

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import PermissionDeniedError
from app.core.roles import Role
from app.core.security import Principal, get_current_principal
from app.modules.departments.service import district_name
from app.modules.users.schemas import CurrentUser, OfficerList
from app.modules.users.service import assignable_officers, get_profile

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=CurrentUser)
async def current_profile(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> CurrentUser:
    profile = await get_profile(session, principal.user_id)
    name = (
        await district_name(session, profile.district_id)
        if profile.district_id is not None
        else None
    )
    return CurrentUser(**profile.model_dump(), district_name=name)


@router.get("", response_model=OfficerList)
async def officers(
    role: Literal["officer"] = Query(),
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> OfficerList:
    """Officers a department may assign: same district and department only."""
    if (
        principal.role != Role.DEPARTMENT
        or principal.district_id is None
        or principal.department_id is None
    ):
        raise PermissionDeniedError("Only a department can list assignable officers.")
    return await assignable_officers(session, principal.district_id, principal.department_id)
