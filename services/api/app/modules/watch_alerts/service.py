"""Business logic for Neighborhood Watch Board.

Alerts are fully anonymous — no reporter identity is stored.
Citizens can post; any authenticated principal can read active alerts;
only Panchayat can mark an alert as actioned.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, PermissionDeniedError
from app.core.roles import Role
from app.core.scope import require_district
from app.core.security import Principal
from app.modules.watch_alerts.models import WatchAlert
from app.modules.watch_alerts.schemas import (
    ActionAck,
    WatchAlertCreate,
    WatchAlertList,
    WatchAlertRead,
)

_ALERT_TTL_HOURS = 72


def _to_read(alert: WatchAlert) -> WatchAlertRead:
    return WatchAlertRead(
        id=alert.id,
        alert_type=alert.alert_type,  # type: ignore[arg-type]
        description=alert.description,
        latitude=alert.latitude,
        longitude=alert.longitude,
        location_label=alert.location_label,
        is_actioned=alert.is_actioned,
        actioned_at=alert.actioned_at,
        expires_at=alert.expires_at,
        created_at=alert.created_at,
        is_demo=alert.is_demo,
    )


async def post_alert(
    session: AsyncSession, principal: Principal, body: WatchAlertCreate
) -> WatchAlertRead:
    """Any citizen can post an anonymous safety alert for their district."""
    if principal.role != Role.CITIZEN:
        raise PermissionDeniedError("Only citizens can post watch alerts.")
    if principal.district_id is None:
        raise PermissionDeniedError("Your account has no assigned district.")

    now = datetime.now(UTC)
    alert = WatchAlert(
        district_id=principal.district_id,
        alert_type=body.alert_type,
        description=body.description,
        latitude=body.latitude,
        longitude=body.longitude,
        location_label=body.location_label,
        expires_at=now + timedelta(hours=_ALERT_TTL_HOURS),
        is_demo=principal.is_demo,
    )
    session.add(alert)
    await session.flush()
    return _to_read(alert)


async def list_alerts(
    session: AsyncSession, principal: Principal
) -> WatchAlertList:
    """Return all non-expired alerts for the principal's district.

    SUPER_ADMIN sees all districts; everyone else is scoped to their district.
    Expired alerts are hidden — clients should show time remaining.
    """
    now = datetime.now(UTC)
    query = select(WatchAlert).where(WatchAlert.expires_at > now)

    if principal.role != Role.SUPER_ADMIN:
        if principal.district_id is None:
            raise PermissionDeniedError("Your account has no assigned district.")
        query = query.where(WatchAlert.district_id == principal.district_id)

    query = query.order_by(WatchAlert.created_at.desc())
    rows = (await session.execute(query)).scalars().all()
    return WatchAlertList(items=[_to_read(r) for r in rows])


async def action_alert(
    session: AsyncSession, principal: Principal, alert_id: UUID
) -> ActionAck:
    """Panchayat marks an alert as actioned (hazard addressed)."""
    if principal.role != Role.PANCHAYAT:
        raise PermissionDeniedError(
            "Only Panchayat accounts can action watch alerts."
        )
    alert = await session.get(WatchAlert, alert_id)
    if alert is None:
        raise NotFoundError("Watch alert not found.")
    require_district(principal, alert.district_id)

    alert.is_actioned = True
    alert.actioned_by = principal.user_id
    alert.actioned_at = datetime.now(UTC)
    return ActionAck(id=alert.id, is_actioned=True)
