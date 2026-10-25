"""Student submissions and institute-scoped faculty reviews."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import DemoMixin, TimestampMixin, UUIDMixin


class Submission(UUIDMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "submissions"
    __table_args__ = (
        CheckConstraint("link IS NULL OR link ~ '^https://[^/[:space:]]+'", name="https_link"),
    )
    team_id: Mapped[UUID] = mapped_column(ForeignKey("teams.id"), index=True)
    statement_id: Mapped[UUID] = mapped_column(ForeignKey("problem_statements.id"), index=True)
    submitted_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(String(2048))
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Review(UUIDMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("submission_id", "reviewer_id"),
        CheckConstraint("score BETWEEN 1 AND 5", name="score_range"),
    )
    submission_id: Mapped[UUID] = mapped_column(ForeignKey("submissions.id"))
    reviewer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    score: Mapped[int]
    comment: Mapped[str] = mapped_column(Text)
