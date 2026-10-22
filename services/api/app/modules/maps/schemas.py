"""Pydantic request/response models for maps.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client and Dart models in packages/contracts.
"""

from pydantic import BaseModel, ConfigDict


class MapsBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# TODO(maps): Create / Update / Read schemas.
