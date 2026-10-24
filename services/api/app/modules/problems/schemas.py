"""Strict report inputs and frontend-compatible read DTOs."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.files.schemas import MediaRead
from app.shared.categories import Category
from app.shared.enums import ProblemStatus, Severity


class ReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    transcript: str = Field(min_length=1, max_length=10000)
    title: str = Field(min_length=1, max_length=200)
    category: Category
    severity: Severity
    summary: str = Field(min_length=1, max_length=5000)
    latitude: Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)]
    longitude: Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)]
    location_label: str = Field(min_length=1, max_length=200)
    channel: Literal["text", "voice"]
    media_ids: list[UUID] = Field(default_factory=list, max_length=3)

    @field_validator("latitude", "longitude", mode="before")
    @classmethod
    def numeric_coordinates(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Coordinates must be JSON numbers")
        return value

    @field_validator("media_ids")
    @classmethod
    def distinct_media(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("A media asset can be attached only once")
        return value


class ReportRead(BaseModel):
    id: UUID
    code: str
    title: str
    description: str
    transcript: str
    reporter_id: UUID
    category: Category
    severity: Severity
    status: ProblemStatus
    status_changed_at: datetime
    ward: str
    district: str
    latitude: float
    longitude: float
    channel: str
    created_at: datetime
    updated_at: datetime
    rejection_reason: str | None
    cluster_id: UUID | None
    is_demo: bool
    media: list[MediaRead]


class ReportList(BaseModel):
    items: list[ReportRead]
