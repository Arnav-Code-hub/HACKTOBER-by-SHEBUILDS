"""Pydantic request/response models for rbac.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client and Dart models in packages/contracts.
"""

from pydantic import BaseModel, ConfigDict


class RbacBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# TODO(rbac): Create / Update / Read schemas.
