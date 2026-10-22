"""Pydantic request/response models for users.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client and Dart models in packages/contracts.
"""

from pydantic import BaseModel, ConfigDict


class UsersBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# TODO(users): Create / Update / Read schemas.
