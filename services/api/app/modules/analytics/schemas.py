"""Pydantic request/response models for analytics.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client and Dart models in packages/contracts.
"""

from pydantic import BaseModel, ConfigDict


class AnalyticsBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# TODO(analytics): Create / Update / Read schemas.
