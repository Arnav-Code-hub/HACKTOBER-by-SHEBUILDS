"""Business logic for notifications. THE PUBLIC FACE of this module.

Templates, channels (FCM/SMS/email) and preferences.

# Module boundary: other modules may import this file and schemas.py.
# They must NEVER import models.py or repository.py — see the import-linter
# contract in pyproject.toml. That rule is what makes this module extractable
# into its own service later without touching a single caller.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.modules.notifications import repository
from app.modules.notifications.schemas import NotificationAck, NotificationList


async def publish_case_update(
    session: AsyncSession,
    recipient_ids: list[UUID],
    *,
    event_key: str,
    title: str,
    body: str,
    resource_type: str,
    resource_id: UUID,
) -> None:
    """Write idempotent in-app updates in the caller's transaction.

    SMS, WhatsApp and push transports can consume these events once configured;
    the in-app inbox works without external provider credentials.
    """
    for recipient_id in set(recipient_ids):
        await repository.create(
            session,
            recipient_id,
            event_key,
            title,
            body,
            resource_type,
            resource_id,
        )


async def inbox(
    session: AsyncSession,
    recipient_id: UUID,
    *,
    limit: int,
    offset: int,
    unread_only: bool,
) -> NotificationList:
    return await repository.list_for_user(session, recipient_id, limit, offset, unread_only)


async def mark_read(
    session: AsyncSession, recipient_id: UUID, notification_id: UUID
) -> NotificationAck:
    result = await repository.mark_read(session, recipient_id, notification_id)
    if result is None:
        raise NotFoundError("Notification not found.")
    return result
