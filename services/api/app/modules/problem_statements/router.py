"""HTTP surface for problem statements, at the agreed /statements paths."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Principal, get_current_principal
from app.modules.problem_statements import service
from app.modules.problem_statements.schemas import StatementCreate, StatementList, StatementRead

router = APIRouter(prefix="/statements", tags=["Problem Statements"])


@router.get("", response_model=StatementList)
async def list_statements(
    status: Literal["draft", "published"] | None = None,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> StatementList:
    return await service.list_statements(session, principal, status)


@router.post("", response_model=StatementRead, status_code=201)
async def create_statement(
    body: StatementCreate,
    key: str = Header(alias="Idempotency-Key", min_length=1, max_length=200, pattern=r"\S"),
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> JSONResponse:
    result = await service.create_statement(session, principal, body, key)
    return JSONResponse(status_code=result.status_code, content=result.body)


@router.post("/{statement_id}/publish", response_model=StatementRead)
async def publish_statement(
    statement_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> StatementRead:
    return await service.publish_statement(session, principal, statement_id)
