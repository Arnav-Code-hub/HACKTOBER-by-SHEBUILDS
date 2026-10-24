"""Integer paise allocations and pledges. No payments are processed."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import DemoMixin, TimestampMixin, UUIDMixin


class Allocation(UUIDMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "allocations"
    __table_args__ = (CheckConstraint("amount_paise > 0", name="positive_amount"),)
    cluster_id: Mapped[UUID] = mapped_column(ForeignKey("clusters.id"), unique=True)
    work_order_id: Mapped[UUID] = mapped_column(ForeignKey("work_orders.id"), unique=True)
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    allocated_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))


class Sponsorship(UUIDMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "sponsorships"
    __table_args__ = (
        CheckConstraint("amount_paise > 0", name="positive_amount"),
        CheckConstraint("status = 'pledged'", name="pledge_only"),
    )
    statement_id: Mapped[UUID] = mapped_column(ForeignKey("problem_statements.id"), index=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    pledged_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(16), default="pledged", server_default="pledged")
    pledged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
