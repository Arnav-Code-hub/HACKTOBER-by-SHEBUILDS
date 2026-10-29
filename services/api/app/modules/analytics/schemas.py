"""Pydantic request/response models for analytics.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client and Dart models in packages/contracts.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, NonNegativeInt

from app.shared.enums import ProblemStatus


class AnalyticsBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PublicTransparency(AnalyticsBase):
    """Anonymous aggregate counts; complaints and grouped cases are distinct.

    Until any live (non-demo) report exists, the totals describe the labelled
    demonstration data and `sample_data` is true. Once live reports exist,
    only live records are counted. Sample and live figures are never mixed.
    """

    report_count: NonNegativeInt
    cluster_count: NonNegativeInt
    active_cases: NonNegativeInt
    citizen_verified_cases: NonNegativeInt
    reports_by_status: dict[ProblemStatus, NonNegativeInt]
    clusters_by_status: dict[ProblemStatus, NonNegativeInt]
    sample_data: bool
    updated_at: datetime | None


class StaffWorkload(AnalyticsBase):
    user_id: UUID
    display_name: str
    email: str
    department_name: str | None
    open_work_orders: int
    funded: int
    in_progress: int
    awaiting_verification: int
    oldest_open_assignment: datetime | None


class StaffWorkloadList(AnalyticsBase):
    items: list[StaffWorkload]
