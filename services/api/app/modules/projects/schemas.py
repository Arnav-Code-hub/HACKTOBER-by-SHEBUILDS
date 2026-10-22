"""Pydantic request/response models for projects.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client and Dart models in packages/contracts.
"""

from pydantic import BaseModel, ConfigDict


class ProjectsBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# TODO(projects): Create / Update / Read schemas.
