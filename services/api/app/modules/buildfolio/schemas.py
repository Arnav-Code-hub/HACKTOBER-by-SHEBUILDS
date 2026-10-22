"""Pydantic request/response models for buildfolio.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client and Dart models in packages/contracts.
"""

from pydantic import BaseModel, ConfigDict


class BuildfolioBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# TODO(buildfolio): Create / Update / Read schemas.
