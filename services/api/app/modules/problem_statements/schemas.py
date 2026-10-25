"""Pydantic request/response models for problem statements.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client in packages/contracts.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StatementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)
    cluster_id: UUID | None = None


class StatementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    body: str
    status: Literal["draft", "published"]
    cluster_id: UUID | None
    published_at: datetime | None


class StatementList(BaseModel):
    items: list[StatementRead]
