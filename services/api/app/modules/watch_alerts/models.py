"""Watch alert SQLAlchemy model."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    false,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import DemoMixin, TimestampMixin, UUIDMixin

ALERT_TYPE_CHECK = (
    "alert_type IN ("
    "'road_hazard','flooding','fire_hazard',"
    "'medical_emergency','suspicious_activity','other')"
)


class WatchAlert(UUIDMixin, TimestampMixin, DemoMixin, Base):
    """An anonymous community safety alert. Expires after 72 hours.

    The posting citizen's identity is intentionally NOT stored so that
    alerts remain fully anonymous. Panchayat staff can mark alerts as
    actioned once the hazard has been addressed.
    """

    __tablename__ = "watch_alerts"
    __table_args__ = (
        CheckConstraint(ALERT_TYPE_CHECK, name="ck_watch_alerts_alert_type"),
        CheckConstraint(
            "latitude BETWEEN -90 AND 90", name="ck_watch_alerts_latitude"
        ),
        CheckConstraint(
            "longitude BETWEEN -180 AND 180",
            name="ck_watch_alerts_longitude",
        ),
    )

    district_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    alert_type: Mapped[str] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(Text)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    location_label: Mapped[str] = mapped_column(String(200))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_actioned: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )
    actioned_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    actioned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
