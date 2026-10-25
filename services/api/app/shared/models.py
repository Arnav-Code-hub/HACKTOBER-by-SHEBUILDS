"""Reusable model mixins. Every table gets id + timestamps from here."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, false, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class DemoMixin:
    """Provenance is persisted, never inferred from a display name."""

    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
