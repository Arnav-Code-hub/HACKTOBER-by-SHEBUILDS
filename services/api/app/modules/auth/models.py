"""Reservations and business changes commit together, never as separate writes."""

from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import DemoMixin, TimestampMixin, UUIDMixin


class IdempotencyKey(UUIDMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (
        UniqueConstraint("user_id", "operation", "key"),
        CheckConstraint("length(trim(key)) > 0", name="nonempty_key"),
        CheckConstraint("length(trim(operation)) > 0", name="nonempty_operation"),
        CheckConstraint("request_hash ~ '^[0-9a-f]{64}$'", name="hash"),
        CheckConstraint("status_code BETWEEN 200 AND 299", name="success_status"),
        CheckConstraint("(status_code IS NULL) = (response_json IS NULL)", name="response_pair"),
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    operation: Mapped[str] = mapped_column(String(100))
    key: Mapped[str] = mapped_column(String(200))
    request_hash: Mapped[str] = mapped_column(String(64))
    status_code: Mapped[int | None]
    response_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
