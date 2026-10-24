"""Validated Cloudinary metadata; delivery URLs are built from trusted references."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import DemoMixin, TimestampMixin, UUIDMixin


class MediaAsset(UUIDMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "media_assets"
    __table_args__ = (
        CheckConstraint("kind IN ('report','completion')", name="kind"),
        CheckConstraint("format IN ('jpg','jpeg','png','webp')", name="format"),
        CheckConstraint("bytes > 0 AND bytes <= 10485760", name="byte_limit"),
        CheckConstraint("width > 0 AND height > 0", name="dimensions"),
        CheckConstraint("version > 0", name="version"),
        CheckConstraint(
            "(kind = 'report' AND work_order_id IS NULL AND round IS NULL) OR "
            "(kind = 'completion' AND report_id IS NULL AND "
            "((work_order_id IS NULL AND round IS NULL) OR "
            "(work_order_id IS NOT NULL AND round IS NOT NULL AND round >= 1)))",
            name="attachment_kind_and_round",
        ),
    )
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    public_id: Mapped[str] = mapped_column(String(255), unique=True)
    asset_id: Mapped[str] = mapped_column(String(128), unique=True)
    version: Mapped[int] = mapped_column(BigInteger)
    kind: Mapped[str] = mapped_column(String(16))
    format: Mapped[str] = mapped_column(String(8))
    bytes: Mapped[int] = mapped_column(BigInteger)
    width: Mapped[int]
    height: Mapped[int]
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    report_id: Mapped[UUID | None] = mapped_column(ForeignKey("reports.id"), index=True)
    work_order_id: Mapped[UUID | None] = mapped_column(ForeignKey("work_orders.id"), index=True)
    round: Mapped[int | None]
