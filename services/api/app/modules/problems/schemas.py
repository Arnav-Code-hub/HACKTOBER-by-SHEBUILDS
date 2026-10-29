"""Strict report inputs and frontend-compatible read DTOs."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    field_validator,
    model_validator,
)

from app.modules.files.schemas import MediaRead
from app.shared.categories import Category
from app.shared.enums import Language, ProblemStatus, Severity


class SuggestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    transcript: str = Field(min_length=1, max_length=2000)


class ReportSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    category: Category
    severity: Severity
    title: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=500)
    mentioned_location: str | None = Field(max_length=200)
    detected_language: Language


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


class FundCluster(BaseModel):
    """A recorded allocation in integer paise; no payment is processed."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    amount_paise: StrictInt = Field(gt=0, le=10**13)
    officer_id: UUID
    notes: str | None = Field(default=None, max_length=500)


class FundResult(BaseModel):
    allocation_id: UUID
    work_order_id: UUID


class WorkOrderRead(BaseModel):
    id: UUID
    cluster_id: UUID
    report_code: str
    title: str
    status: ProblemStatus
    round: int = Field(ge=1)
    location_label: str | None
    instructions: str | None
    notes: str | None
    allocated_paise: int = Field(ge=0)
    assigned_at: datetime


class WorkOrderList(BaseModel):
    items: list[WorkOrderRead]


class WorkOrderUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    notes: str = Field(min_length=1, max_length=1000)


class CompleteWorkOrder(BaseModel):
    model_config = ConfigDict(extra="forbid")
    media_ids: list[UUID] = Field(min_length=1, max_length=3)
    # The round the officer was shown; a request from before a citizen
    # returned the work must not become the correction.
    expected_round: int = Field(ge=1)

    @field_validator("media_ids")
    @classmethod
    def distinct_media(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("A photo can be attached only once")
        return value


class EvidencePhotoRead(BaseModel):
    url: str
    uploaded_at: datetime


class EvidenceRead(BaseModel):
    """Before/after evidence for one work order — for human review, not proof."""

    report_code: str
    status: ProblemStatus
    before: EvidencePhotoRead | None
    after: EvidencePhotoRead | None
    after_round: int | None
    card_url: str | None
    verdict_label: str | None = None
    # The citizen's reason when the round shown was returned for correction.
    returned_comment: str | None = None


class VerificationRead(EvidenceRead):
    work_order_id: UUID
    title: str
    category: Category
    round: int = Field(ge=1)
    can_verify: bool
    blocked_reason: str | None


WaitingOn = Literal["department", "officer", "citizen", "none"]


class CaseRead(BaseModel):
    """One case from prioritisation to citizen verification, with its allocation."""

    cluster_id: UUID
    report_code: str
    title: str
    category: Category
    status: ProblemStatus
    # Who must act next: the department funds, the officer works, the
    # citizen verifies; "none" once the citizen has confirmed the repair.
    waiting_on: WaitingOn
    status_changed_at: datetime
    work_order_id: UUID | None
    round: int | None = Field(default=None, ge=1)
    department_name: str | None
    officer_name: str | None
    allocated_paise: int | None = Field(default=None, ge=0)
    allocated_at: datetime | None
    allocated_by_name: str | None


class CaseList(BaseModel):
    items: list[CaseRead]


class VerifyWorkOrder(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    verdict: StrictBool
    expected_round: StrictInt = Field(ge=1, le=2147483647)
    comment: str | None = Field(default=None, max_length=500)

    @field_validator("comment")
    @classmethod
    def empty_comment(cls, value: str | None) -> str | None:
        return value or None
