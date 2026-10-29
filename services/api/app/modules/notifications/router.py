"""HTTP surface for notifications. Routing and validation only.

Business logic belongs in service.py; this file translates HTTP to it.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Principal, get_current_principal
from app.modules.notifications import service
from app.modules.notifications.schemas import NotificationAck, NotificationList

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationList)
async def inbox(
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> NotificationList:
    return await service.inbox(
        session,
        principal.user_id,
        limit=limit,
        offset=offset,
        unread_only=unread_only,
    )


@router.post("/{notification_id}/read", response_model=NotificationAck)
async def mark_read(
    notification_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> NotificationAck:
    return await service.mark_read(session, principal.user_id, notification_id)
