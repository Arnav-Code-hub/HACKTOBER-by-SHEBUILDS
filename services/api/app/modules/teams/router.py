from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Principal, get_current_principal
from app.modules.teams import service
from app.modules.teams.schemas import TeamCreate, TeamList, TeamRead

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.get("", response_model=TeamList)
async def list_teams(
    mine: bool = False,
    institute: Literal["me"] | None = None,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> TeamList:
    return await service.list_teams(session, principal, mine, institute)


@router.post("", response_model=TeamRead, status_code=201)
async def create_team(
    body: TeamCreate,
    key: str = Header(alias="Idempotency-Key", min_length=1, max_length=200, pattern=r"\S"),
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> JSONResponse:
    result = await service.create_team(session, principal, body, key)
    return JSONResponse(status_code=result.status_code, content=result.body)


@router.post("/{identity}/approve", response_model=TeamRead)
async def approve_team(
    identity: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> TeamRead:
    return await service.approve_team(session, principal, identity)
