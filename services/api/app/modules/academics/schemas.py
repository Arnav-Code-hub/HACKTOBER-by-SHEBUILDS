"""Pydantic request/response models for academics.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client and Dart models in packages/contracts.
"""

from pydantic import BaseModel, ConfigDict


class AcademicsBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# TODO(academics): Create / Update / Read schemas.
