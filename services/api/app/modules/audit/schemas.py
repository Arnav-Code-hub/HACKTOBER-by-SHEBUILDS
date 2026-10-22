"""Pydantic request/response models for audit.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client and Dart models in packages/contracts.
"""

from pydantic import BaseModel, ConfigDict


class AuditBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# TODO(audit): Create / Update / Read schemas.
