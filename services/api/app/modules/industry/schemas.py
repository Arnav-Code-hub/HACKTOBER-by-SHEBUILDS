"""Pydantic request/response models for industry.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client and Dart models in packages/contracts.
"""

from pydantic import BaseModel, ConfigDict


class IndustryBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# TODO(industry): Create / Update / Read schemas.
