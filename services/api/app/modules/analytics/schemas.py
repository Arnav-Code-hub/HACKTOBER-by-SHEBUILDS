"""Pydantic request/response models for analytics.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client and Dart models in packages/contracts.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, NonNegativeInt

from app.shared.enums import ProblemStatus


class AnalyticsBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PublicTransparency(AnalyticsBase):
    """Anonymous aggregate counts; complaints and grouped cases are distinct."""

    report_count: NonNegativeInt
    cluster_count: NonNegativeInt
    active_cases: NonNegativeInt
    citizen_verified_cases: NonNegativeInt
    reports_by_status: dict[ProblemStatus, NonNegativeInt]
    clusters_by_status: dict[ProblemStatus, NonNegativeInt]
    demo_data_excluded: Literal[True] = True
    updated_at: datetime | None
