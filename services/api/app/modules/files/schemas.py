"""Pydantic request/response models for files.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client and Dart models in packages/contracts.
"""

from pydantic import BaseModel, ConfigDict


class FilesBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# TODO(files): Create / Update / Read schemas.
