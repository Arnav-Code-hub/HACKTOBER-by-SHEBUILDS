"""Pydantic request/response models for notifications.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client and Dart models in packages/contracts.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationsBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class NotificationRead(NotificationsBase):
    id: UUID
    event_key: str
    title: str
    body: str
    resource_type: str
    resource_id: UUID
    created_at: datetime
    read_at: datetime | None


class NotificationList(NotificationsBase):
    items: list[NotificationRead]
    unread_count: int


class NotificationAck(NotificationsBase):
    id: UUID
    read_at: datetime
