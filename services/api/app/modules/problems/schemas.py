"""Pydantic request/response models for problems.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client and Dart models in packages/contracts.
"""

from pydantic import BaseModel, ConfigDict


class ProblemsBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# TODO(problems): Create / Update / Read schemas.
