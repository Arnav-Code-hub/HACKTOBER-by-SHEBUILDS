from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Principal, get_current_principal
from app.modules.projects import service
from app.modules.projects.schemas import (
    ReviewCreate,
    ReviewResult,
    SubmissionCreate,
    SubmissionList,
    SubmissionRead,
)

router = APIRouter(prefix="/submissions", tags=["Submissions"])


@router.get("", response_model=SubmissionList)
async def list_submissions(
    mine: bool = False,
    institute: Literal["me"] | None = None,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> SubmissionList:
    return await service.list_submissions(session, principal, mine, institute)


@router.post("", response_model=SubmissionRead, status_code=201)
async def create_submission(
    body: SubmissionCreate,
    key: str = Header(alias="Idempotency-Key", min_length=1, max_length=200, pattern=r"\S"),
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> JSONResponse:
    result = await service.create_submission(session, principal, body, key)
    return JSONResponse(status_code=result.status_code, content=result.body)


@router.post("/{identity}/reviews", response_model=ReviewResult, status_code=201)
async def review_submission(
    identity: UUID,
    body: ReviewCreate,
    key: str = Header(alias="Idempotency-Key", min_length=1, max_length=200, pattern=r"\S"),
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> JSONResponse:
    result = await service.review_submission(session, principal, identity, body, key)
    return JSONResponse(status_code=result.status_code, content=result.body)
