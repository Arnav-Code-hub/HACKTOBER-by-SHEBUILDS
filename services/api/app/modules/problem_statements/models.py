"""Published student challenges are independent of public work orders."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import DemoMixin, TimestampMixin, UUIDMixin


class ProblemStatement(UUIDMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "problem_statements"
    __table_args__ = (
        CheckConstraint("status IN ('draft','published')", name="status"),
        CheckConstraint("status <> 'published' OR published_at IS NOT NULL", name="publish_date"),
    )
    department_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    district_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    cluster_id: Mapped[UUID | None] = mapped_column(ForeignKey("clusters.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
