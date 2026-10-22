"""Pydantic request/response models for feedback.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client and Dart models in packages/contracts.
"""

from pydantic import BaseModel, ConfigDict


class FeedbackBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# TODO(feedback): Create / Update / Read schemas.
