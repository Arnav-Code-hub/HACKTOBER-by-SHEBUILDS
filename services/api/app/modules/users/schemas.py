"""Profile returned to both clients; roles/scopes originate in PostgreSQL."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.roles import Role


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    firebase_uid: str
    role: Role
    display_name: str
    email: str
    district_id: UUID | None
    department_id: UUID | None
    institute_id: UUID | None
    organization_id: UUID | None
    is_demo: bool


class CurrentUser(UserProfile):
    """`GET /users/me`: the profile plus its district's display name."""

    district_name: str | None


class OfficerSummary(BaseModel):
    id: UUID
    display_name: str | None
    email: str | None


class OfficerList(BaseModel):
    items: list[OfficerSummary]
