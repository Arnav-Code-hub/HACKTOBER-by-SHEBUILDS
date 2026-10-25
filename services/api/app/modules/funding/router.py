from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Principal, get_current_principal
from app.modules.funding import pledge_service as service
from app.modules.funding.pledge_schemas import PledgeCreate, PledgeList, PledgeRead

router = APIRouter(tags=["Sponsorships"])


@router.get("/sponsorships", response_model=PledgeList)
async def list_pledges(
    mine: bool = False,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> PledgeList:
    return await service.list_pledges(session, principal, mine)


@router.post("/statements/{identity}/sponsorships", response_model=PledgeRead, status_code=201)
async def create_pledge(
    identity: UUID,
    body: PledgeCreate,
    key: str = Header(alias="Idempotency-Key", min_length=1, max_length=200, pattern=r"\S"),
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> JSONResponse:
    result = await service.create_pledge(session, principal, identity, body, key)
    return JSONResponse(status_code=result.status_code, content=result.body)
