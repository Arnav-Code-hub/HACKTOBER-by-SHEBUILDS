"""Oversight and privileged administration HTTP endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Principal, get_current_principal
from app.modules.audit import service
from app.modules.audit.schemas import (
    AdminSummary,
    AdminUserChange,
    AdminUserList,
    AdminUserRead,
    AuditList,
    OrganizationList,
)

router = APIRouter(tags=["Administration"])


@router.get("/admin/summary", response_model=AdminSummary)
async def summary(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> AdminSummary:
    return await service.summary(session, principal)


@router.get("/admin/users", response_model=AdminUserList)
async def users(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> AdminUserList:
    return await service.users(session, principal)


@router.get("/organizations", response_model=OrganizationList)
async def organizations(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> OrganizationList:
    return await service.organizations(session, principal)


@router.get("/admin/audit", response_model=AuditList)
async def audit(
    limit: int = Query(default=50, ge=1, le=200),
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> AuditList:
    return await service.audit_list(session, principal, limit)


@router.patch("/admin/users/{identity}", response_model=AdminUserRead)
async def change_user(
    identity: UUID,
    body: AdminUserChange,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> AdminUserRead:
    return await service.change_user(session, principal, identity, body)
