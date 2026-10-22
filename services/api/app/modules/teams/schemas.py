"""Pydantic request/response models for teams.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client and Dart models in packages/contracts.
"""

from pydantic import BaseModel, ConfigDict


class TeamsBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# TODO(teams): Create / Update / Read schemas.
