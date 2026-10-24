"""Citizen endpoints under the frontend's agreed /reports paths."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Principal, get_current_principal
from app.integrations.cloudinary import MediaProvider, get_media_provider
from app.modules.problems import service
from app.modules.problems.schemas import ReportCreate, ReportList, ReportRead

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("", response_model=ReportRead, status_code=201)
async def create(
    body: ReportCreate,
    key: str = Header(alias="Idempotency-Key", min_length=1, max_length=200, pattern=r"\S"),
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
    provider: MediaProvider = Depends(get_media_provider),
) -> JSONResponse:
    result = await service.create_report(session, principal, body, key, provider)
    return JSONResponse(status_code=result.status_code, content=result.body)


@router.get("", response_model=ReportList)
async def mine(
    mine: bool = True,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
    provider: MediaProvider = Depends(get_media_provider),
) -> ReportList:
    return await service.list_reports(
        session, principal, provider, mine=mine, limit=limit, offset=offset
    )


@router.get("/{report_id}", response_model=ReportRead)
async def detail(
    report_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
    provider: MediaProvider = Depends(get_media_provider),
) -> ReportRead:
    return await service.get_report(session, principal, report_id, provider)
