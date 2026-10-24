"""Institutional participation requires an explicit approval."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import DemoMixin, TimestampMixin, UUIDMixin


class Team(UUIDMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "teams"
    __table_args__ = (
        CheckConstraint(
            "NOT institute_approved OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)",
            name="approval_evidence",
        ),
    )
    name: Mapped[str] = mapped_column(String(200))
    institute_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    statement_id: Mapped[UUID] = mapped_column(ForeignKey("problem_statements.id"), index=True)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    institute_approved: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    approved_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TeamMember(UUIDMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "team_members"
    __table_args__ = (UniqueConstraint("team_id", "user_id"),)
    team_id: Mapped[UUID] = mapped_column(ForeignKey("teams.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
