"""Pydantic request/response models for leaderboard.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client and Dart models in packages/contracts.
"""

from pydantic import BaseModel, ConfigDict


class LeaderboardBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# TODO(leaderboard): Create / Update / Read schemas.
