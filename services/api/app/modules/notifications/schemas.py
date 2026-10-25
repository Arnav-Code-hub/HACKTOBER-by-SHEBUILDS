"""Pydantic request/response models for notifications.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client and Dart models in packages/contracts.
"""

from pydantic import BaseModel, ConfigDict


class NotificationsBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# TODO(notifications): Create / Update / Read schemas.
