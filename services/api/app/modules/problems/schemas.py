"""Strict report inputs and frontend-compatible read DTOs."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    # How the citizen started the report; provenance only, never a ranking input.
    channel: Literal["text", "voice", "photo", "location"]
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


class ScoreFactor(BaseModel):
    factor: Literal["support", "gap", "equity", "severity", "age"]
    label: str
    score: float = Field(ge=0, le=100)
    weight: float = Field(ge=0, le=1)
    is_demo: bool


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
    rank: int | None = None
    total_ranked: int | None = None
    priority_score: float | None = None
    supporter_count: int | None = None
    score_breakdown: list[ScoreFactor] | None = None


class ReportList(BaseModel):
    items: list[ReportRead]


class ValidateReport(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    decision: Literal["verify", "reject"]
    reason: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def rejection_needs_reason(self) -> "ValidateReport":
        if self.decision == "reject" and not self.reason:
            raise ValueError("A rejection reason is required")
        return self


class AssignCluster(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cluster_id: UUID | None = None
    new: Literal[True] | None = None

    @field_validator("new", mode="before")
    @classmethod
    def explicit_new(cls, value: object) -> object:
        if value is not True and value is not None:
            raise ValueError("New must be true")
        return value

    @model_validator(mode="after")
    def exactly_one_target(self) -> "AssignCluster":
        if (self.cluster_id is not None) == (self.new is True):
            raise ValueError("Choose an existing cluster or start a new one")
        return self


class StatusAck(BaseModel):
    id: UUID
    status: ProblemStatus


class ClusterSuggestion(BaseModel):
    id: UUID
    title: str
    category: Category
    distance_m: float = Field(ge=0)
    report_count: int = Field(ge=1)
    supporter_count: int = Field(ge=0)


class ClusterSuggestions(BaseModel):
    items: list[ClusterSuggestion]


class RankedCluster(BaseModel):
    id: UUID
    title: str
    category: Category
    status: ProblemStatus
    rank: int = Field(ge=1)
    priority_score: float = Field(ge=0, le=100)
    supporter_count: int = Field(ge=0)
    report_count: int = Field(ge=1)
    anchor_report_code: str
    infrastructure_gap: float = Field(ge=0, le=100)
    equity_index: float = Field(ge=0, le=100)
    inputs_are_demo: bool
    score_breakdown: list[ScoreFactor]


class RankedClusters(BaseModel):
    items: list[RankedCluster]


class RankingInputs(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    infrastructure_gap: float = Field(ge=0, le=100)
    equity_index: float = Field(ge=0, le=100)

    @field_validator("infrastructure_gap", "equity_index", mode="before")
    @classmethod
    def numbers_only(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Ranking inputs must be JSON numbers")
        return value


class IdentityAck(BaseModel):
    id: UUID


class SupportAck(BaseModel):
    id: UUID
    supporter_count: int = Field(ge=0)
