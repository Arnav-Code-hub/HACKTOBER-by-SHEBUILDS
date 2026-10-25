"""Persist issued media upload authorizations.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "upload_intents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("public_id", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("content_type", sa.String(32), nullable=False),
        sa.Column("declared_bytes", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_asset_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.CheckConstraint("kind IN ('report','completion')", name=op.f("ck_upload_intents_kind")),
        sa.CheckConstraint(
            "declared_bytes > 0 AND declared_bytes <= 10485760",
            name=op.f("ck_upload_intents_byte_limit"),
        ),
        sa.CheckConstraint(
            "content_type IN ('image/jpeg','image/png','image/webp')",
            name=op.f("ck_upload_intents_content_type"),
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_upload_intents_owner_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["completed_asset_id"],
            ["media_assets.id"],
            name=op.f("fk_upload_intents_completed_asset_id_media_assets"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_upload_intents")),
        sa.UniqueConstraint("public_id", name=op.f("uq_upload_intents_public_id")),
        sa.UniqueConstraint(
            "completed_asset_id", name=op.f("uq_upload_intents_completed_asset_id")
        ),
    )
    op.create_index(op.f("ix_upload_intents_owner_id"), "upload_intents", ["owner_id"])
    op.create_index(op.f("ix_upload_intents_expires_at"), "upload_intents", ["expires_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_upload_intents_expires_at"), table_name="upload_intents")
    op.drop_index(op.f("ix_upload_intents_owner_id"), table_name="upload_intents")
    op.drop_table("upload_intents")
