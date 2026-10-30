"""Only supervision and delivery state; council code remains in its own repository."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import TimestampMixin, UUIDMixin


class TeamSupervisor(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "team_supervisors"
    team_id: Mapped[UUID] = mapped_column(ForeignKey("teams.id"), unique=True)
    faculty_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    assigned_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))


class CouncilAssessment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "council_assessments"
    __table_args__ = (
        UniqueConstraint("requested_by", "request_key"),
        CheckConstraint(
            "status IN ('queued','reviewing','incomplete','delivery_failed','available')",
            name="status",
        ),
        CheckConstraint("completed_reviewers BETWEEN 0 AND 5", name="reviewer_count"),
        CheckConstraint(
            "status != 'available' OR "
            "(report IS NOT NULL AND pdf IS NOT NULL AND delivered_at IS NOT NULL)",
            name="publication_artifacts",
        ),
    )
    submission_id: Mapped[UUID] = mapped_column(ForeignKey("submissions.id"), index=True)
    team_id: Mapped[UUID] = mapped_column(ForeignKey("teams.id"), index=True)
    supervisor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    supervisor_name: Mapped[str] = mapped_column(String(200))
    requested_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    request_key: Mapped[str] = mapped_column(String(200))
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(24), default="queued")
    remote_id: Mapped[UUID | None]
    completed_reviewers: Mapped[int] = mapped_column(default=0)
    retry_requested: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    retry_key: Mapped[str | None] = mapped_column(String(36))
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    report: Mapped[dict[str, Any] | None] = mapped_column(JSON(none_as_null=True))
    pdf: Mapped[bytes | None] = mapped_column(LargeBinary)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
