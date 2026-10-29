"""HTTP surface for Neighborhood Watch Board. Routing and validation only."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Principal, get_current_principal
from app.modules.watch_alerts import service
from app.modules.watch_alerts.schemas import (
    ActionAck,
    WatchAlertCreate,
    WatchAlertList,
    WatchAlertRead,
)

router = APIRouter(prefix="/watch-alerts", tags=["Watch Alerts"])


@router.post("", response_model=WatchAlertRead, status_code=201)
async def post_alert(
    body: WatchAlertCreate,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> WatchAlertRead:
    """Post an anonymous safety alert to the community watch board."""
    return await service.post_alert(session, principal, body)


@router.get("", response_model=WatchAlertList)
async def list_alerts(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> WatchAlertList:
    """Return all active (non-expired) watch alerts for the principal's district."""
    return await service.list_alerts(session, principal)


@router.patch("/{alert_id}/action", response_model=ActionAck)
async def action_alert(
    alert_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> ActionAck:
    """Panchayat marks a watch alert as actioned (hazard addressed)."""
    return await service.action_alert(session, principal, alert_id)
