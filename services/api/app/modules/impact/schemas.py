"""Pydantic request/response models for impact.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client and Dart models in packages/contracts.
"""

from pydantic import BaseModel, ConfigDict


class ImpactBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# TODO(impact): Create / Update / Read schemas.
