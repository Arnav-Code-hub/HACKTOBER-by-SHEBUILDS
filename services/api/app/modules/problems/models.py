"""Reports retain intake status; clusters alone own the execution lifecycle."""

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
    UniqueConstraint,
    false,
    func,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.categories import CATEGORY_CHECK
from app.shared.models import DemoMixin, TimestampMixin, UUIDMixin


class Report(UUIDMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint("status IN ('reported','verified','rejected')", name="intake_status"),
        CheckConstraint(CATEGORY_CHECK, name="category"),
        CheckConstraint("severity IN ('low','medium','high','critical')", name="severity"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude"),
        CheckConstraint("channel IN ('text','voice','photo','location')", name="channel"),
        CheckConstraint(
            "status <> 'rejected' OR (rejection_reason IS NOT NULL "
            "AND length(trim(rejection_reason)) > 0)",
            name="rejection_reason",
        ),
        CheckConstraint("cluster_id IS NULL OR status = 'verified'", name="validated_membership"),
    )
    code: Mapped[str] = mapped_column(
        String(40), unique=True, server_default=text("'JM-' || nextval('report_code_seq')::text")
    )
    reporter_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    district_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    transcript: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(24))
    severity: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32), default="reported")
    status_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    location_label: Mapped[str] = mapped_column(String(200))
    channel: Mapped[str] = mapped_column(String(16), default="text")
    # Named ALTER breaks the report/cluster anchor cycle in both migration directions.
    cluster_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("clusters.id", use_alter=True, name="fk_reports_cluster_id_clusters"), index=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    # Senior / disability priority flag — recorded at intake, never inferred.
    affects_seniors: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )


class Cluster(UUIDMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "clusters"
    __table_args__ = (
        CheckConstraint(CATEGORY_CHECK, name="category"),
        CheckConstraint(
            "status IN ('prioritised','funded','in_progress',"
            "'awaiting_verification','citizen_verified')",
            name="execution_status",
        ),
        CheckConstraint("infrastructure_gap BETWEEN 0 AND 100", name="gap_range"),
        CheckConstraint("equity_index BETWEEN 0 AND 100", name="equity_range"),
    )
    district_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    category: Mapped[str] = mapped_column(String(24))
    anchor_report_id: Mapped[UUID] = mapped_column(ForeignKey("reports.id"), unique=True)
    status: Mapped[str] = mapped_column(String(32), default="prioritised")
    status_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    infrastructure_gap: Mapped[float | None] = mapped_column(Float)
    equity_index: Mapped[float | None] = mapped_column(Float)
    inputs_are_demo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


class Support(UUIDMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "supports"
    __table_args__ = (UniqueConstraint("cluster_id", "user_id"),)
    cluster_id: Mapped[UUID] = mapped_column(ForeignKey("clusters.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)


class WorkOrder(UUIDMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "work_orders"
    __table_args__ = (CheckConstraint("round >= 1", name="positive_round"),)
    cluster_id: Mapped[UUID] = mapped_column(ForeignKey("clusters.id"), unique=True)
    department_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    district_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    officer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    round: Mapped[int] = mapped_column(default=1, server_default=text("1"))
    notes: Mapped[str] = mapped_column(Text, default="", server_default="")
    instructions: Mapped[str] = mapped_column(Text, default="", server_default="")
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Verification(UUIDMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "verifications"
    __table_args__ = (
        UniqueConstraint("work_order_id", "round"),
        CheckConstraint("round >= 1", name="positive_round"),
        CheckConstraint("length(comment) <= 500", name="comment_length"),
    )
    work_order_id: Mapped[UUID] = mapped_column(ForeignKey("work_orders.id"))
    round: Mapped[int]
    citizen_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    verdict: Mapped[bool]
    comment: Mapped[str | None] = mapped_column(Text)
