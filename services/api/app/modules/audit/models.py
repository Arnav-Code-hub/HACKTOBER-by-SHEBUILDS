"""Audit events carry historical actor role and affected district scope."""

from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import DemoMixin, TimestampMixin, UUIDMixin


class AuditEventRecord(UUIDMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_events_district_created", "district_id", "created_at"),)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    actor_role: Mapped[str] = mapped_column(String(24))
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[UUID]
    district_id: Mapped[UUID | None] = mapped_column(ForeignKey("organizations.id"))
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    reason: Mapped[str | None] = mapped_column(Text)
