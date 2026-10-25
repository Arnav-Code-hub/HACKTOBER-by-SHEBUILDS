"""Pydantic request/response models for funding.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client and Dart models in packages/contracts.
"""

from pydantic import BaseModel, ConfigDict


class FundingBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# TODO(funding): Create / Update / Read schemas.
