"""Pydantic schemas for Watch Alert DTOs."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

AlertType = Literal[
    "road_hazard",
    "flooding",
    "fire_hazard",
    "medical_emergency",
    "suspicious_activity",
    "other",
]


class WatchAlertCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    alert_type: AlertType
    description: str = Field(min_length=1, max_length=500)
    latitude: Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)]
    longitude: Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)]
    location_label: str = Field(min_length=1, max_length=200)

    @field_validator("latitude", "longitude", mode="before")
    @classmethod
    def numeric_coordinates(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Coordinates must be JSON numbers")
        return value


class WatchAlertRead(BaseModel):
    id: UUID
    alert_type: AlertType
    description: str
    latitude: float
    longitude: float
    location_label: str
    is_actioned: bool
    actioned_at: datetime | None
    expires_at: datetime
    created_at: datetime
    is_demo: bool


class WatchAlertList(BaseModel):
    items: list[WatchAlertRead]


class ActionAck(BaseModel):
    id: UUID
    is_actioned: bool
