"""Pydantic request/response models for geography.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client and Dart models in packages/contracts.
"""

from pydantic import BaseModel, ConfigDict


class GeographyBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# TODO(geography): Create / Update / Read schemas.
