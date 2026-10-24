"""Organization hierarchy and one responsible department per district/category."""

from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.categories import CATEGORY_CHECK
from app.shared.models import DemoMixin, TimestampMixin, UUIDMixin


class Organization(UUIDMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint("type IN ('district','department','institute','industry')", name="type"),
    )
    type: Mapped[str] = mapped_column(String(24))
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


class DepartmentCategory(UUIDMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "department_categories"
    __table_args__ = (
        UniqueConstraint("district_id", "category"),
        CheckConstraint(CATEGORY_CHECK, name="category"),
    )
    department_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    district_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    category: Mapped[str] = mapped_column(String(24))
