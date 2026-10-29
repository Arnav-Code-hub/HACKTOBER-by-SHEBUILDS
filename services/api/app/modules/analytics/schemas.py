"""Pydantic request/response models for analytics.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client and Dart models in packages/contracts.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AnalyticsBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DistrictTransparency(AnalyticsBase):
    district_name: str
    report_count: int
    cluster_count: int
    active_cases: int
    citizen_verified_cases: int
    allocated_paise: int
    last_updated: datetime | None


class PublicTransparency(AnalyticsBase):
    updated_at: datetime | None
    demo_data_excluded: bool = True
    report_count: int
    cluster_count: int
    active_cases: int
    citizen_verified_cases: int
    allocated_paise: int
    reports_by_status: dict[str, int]
    clusters_by_status: dict[str, int]
    districts: list[DistrictTransparency]


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
