"""Database access for notifications. PRIVATE to this module.

Only service.py in this module may call these functions.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import Notification
from app.modules.notifications.schemas import NotificationAck, NotificationList, NotificationRead


async def create(
    session: AsyncSession,
    recipient_id: UUID,
    event_key: str,
    title: str,
    body: str,
    resource_type: str,
    resource_id: UUID,
) -> None:
    await session.execute(
        insert(Notification)
        .values(
            recipient_id=recipient_id,
            event_key=event_key,
            title=title,
            body=body,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        .on_conflict_do_nothing(
            index_elements=["recipient_id", "event_key", "resource_type", "resource_id"]
        )
    )


async def list_for_user(
    session: AsyncSession,
    recipient_id: UUID,
    limit: int,
    offset: int,
    unread_only: bool,
) -> NotificationList:
    filters = [Notification.recipient_id == recipient_id]
    if unread_only:
        filters.append(Notification.read_at.is_(None))
    items = (
        await session.scalars(
            select(Notification)
            .where(*filters)
            .order_by(Notification.created_at.desc(), Notification.id)
            .limit(limit)
            .offset(offset)
        )
    ).all()
    unread_count = await session.scalar(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.recipient_id == recipient_id,
            Notification.read_at.is_(None),
        )
    )
    return NotificationList(
        items=[NotificationRead.model_validate(item) for item in items],
        unread_count=unread_count or 0,
    )


async def mark_read(
    session: AsyncSession, recipient_id: UUID, notification_id: UUID
) -> NotificationAck | None:
    now = datetime.now(UTC)
    row = await session.scalar(
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.recipient_id == recipient_id,
        )
        .values(read_at=func.coalesce(Notification.read_at, now))
        .returning(Notification)
    )
    if row is None:
        return None
    return NotificationAck(id=row.id, read_at=row.read_at or now)
