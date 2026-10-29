"""Add watch_alerts table and affects_seniors flag on reports.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ALERT_TYPES = (
    "road_hazard",
    "flooding",
    "fire_hazard",
    "medical_emergency",
    "suspicious_activity",
    "other",
)


def upgrade() -> None:
    # -- Neighborhood Watch Board table --
    op.create_table(
        "watch_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "district_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("alert_type", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("location_label", sa.String(length=200), nullable=False),
        sa.Column(
            "expires_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column(
            "is_actioned", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "actioned_by", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column(
            "actioned_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "is_demo", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "alert_type IN ("
            + ", ".join(f"'{t}'" for t in ALERT_TYPES)
            + ")",
            name="ck_watch_alerts_alert_type",
        ),
        sa.CheckConstraint(
            "latitude BETWEEN -90 AND 90", name="ck_watch_alerts_latitude"
        ),
        sa.CheckConstraint(
            "longitude BETWEEN -180 AND 180",
            name="ck_watch_alerts_longitude",
        ),
        sa.ForeignKeyConstraint(
            ["district_id"],
            ["organizations.id"],
            name="fk_watch_alerts_district_id_organizations",
        ),
        sa.ForeignKeyConstraint(
            ["actioned_by"],
            ["users.id"],
            name="fk_watch_alerts_actioned_by_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_watch_alerts"),
    )
    op.create_index(
        "ix_watch_alerts_district_expires",
        "watch_alerts",
        ["district_id", "expires_at"],
    )

    # -- Senior Citizen Priority Flag on reports --
    op.add_column(
        "reports",
        sa.Column(
            "affects_seniors",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("reports", "affects_seniors")
    op.drop_index("ix_watch_alerts_district_expires", table_name="watch_alerts")
    op.drop_table("watch_alerts")
