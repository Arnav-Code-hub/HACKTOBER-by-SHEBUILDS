"""Pydantic request/response models for departments.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client and Dart models in packages/contracts.
"""

from pydantic import BaseModel, ConfigDict


class DepartmentsBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# TODO(departments): Create / Update / Read schemas.
