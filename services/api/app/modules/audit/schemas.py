"""Oversight contracts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.roles import Role


class AdminUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    display_name: str
    email: str
    role: Role
    district_id: UUID | None
    department_id: UUID | None
    institute_id: UUID | None
    organization_id: UUID | None
    is_active: bool


class AdminUserList(BaseModel):
    items: list[AdminUserRead]


class AdminUserChange(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    role: Role
    district_id: UUID | None
    department_id: UUID | None
    institute_id: UUID | None
    organization_id: UUID | None = None
    reason: str = Field(min_length=1, max_length=300)


class AdminUserStatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    is_active: bool
    reason: str = Field(min_length=1, max_length=300)


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    type: Literal["district", "department", "institute", "industry"]
    name: str


class OrganizationList(BaseModel):
    items: list[OrganizationRead]


class AuditRead(BaseModel):
    id: UUID
    at: datetime
    actor_name: str
    actor_role: Role
    action: str
    entity_type: str
    entity_id: UUID
    reason: str | None


class AuditList(BaseModel):
    items: list[AuditRead]


class AdminSummary(BaseModel):
    district_name: str
    reports_by_status: dict[str, int]
    cluster_count: int
    work_orders_by_status: dict[str, int]
    allocated_paise: int
    pledged_paise: int
