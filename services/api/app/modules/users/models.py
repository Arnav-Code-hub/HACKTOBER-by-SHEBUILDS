"""Firebase owns passwords; the database owns provisioned identities and scope."""

from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, true
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.roles import Role
from app.shared.models import DemoMixin, TimestampMixin, UUIDMixin


class User(UUIDMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN (" + ",".join(f"'{r}'" for r in Role) + ")", name="role"),
    )
    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True)
    email: Mapped[str] = mapped_column(String(320))
    display_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(24), index=True)
    district_id: Mapped[UUID | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    department_id: Mapped[UUID | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    institute_id: Mapped[UUID | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("organizations.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
