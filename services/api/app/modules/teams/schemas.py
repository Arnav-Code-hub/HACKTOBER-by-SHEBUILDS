"""Team contracts shared by the student and institute workspaces."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TeamCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=200)
    statement_id: UUID


class TeamRead(BaseModel):
    id: UUID
    name: str
    statement_id: UUID
    statement_title: str
    institute_approved: bool
    member_count: int
    created_at: datetime


class TeamList(BaseModel):
    items: list[TeamRead]
