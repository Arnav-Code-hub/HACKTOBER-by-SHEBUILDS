"""Supervisor assignments and independent council delivery outbox.
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


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "team_supervisors",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("team_id", uuid, sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("faculty_id", uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assigned_by", uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("team_id"),
    )
    op.create_index("ix_team_supervisors_faculty_id", "team_supervisors", ["faculty_id"])
    op.create_table(
        "council_assessments",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("submission_id", uuid, sa.ForeignKey("submissions.id"), nullable=False),
        sa.Column("team_id", uuid, sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("supervisor_id", uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("supervisor_name", sa.String(200), nullable=False),
        sa.Column("requested_by", uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("request_key", sa.String(200), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("remote_id", uuid, nullable=True),
        sa.Column("completed_reviewers", sa.Integer(), nullable=False),
        sa.Column("retry_requested", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("retry_key", sa.String(36), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("report", sa.JSON(none_as_null=True), nullable=True),
        sa.Column("pdf", sa.LargeBinary(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("requested_by", "request_key"),
        sa.CheckConstraint(
            "status IN ('queued','reviewing','incomplete','delivery_failed','available')",
            name=op.f("ck_council_assessments_status"),
        ),
        sa.CheckConstraint(
            "completed_reviewers BETWEEN 0 AND 5",
            name=op.f("ck_council_assessments_reviewer_count"),
        ),
        sa.CheckConstraint(
            "status != 'available' OR "
            "(report IS NOT NULL AND pdf IS NOT NULL AND delivered_at IS NOT NULL)",
            name=op.f("ck_council_assessments_publication_artifacts"),
        ),
    )
    for column in ["submission_id", "team_id", "supervisor_id", "next_attempt_at"]:
        op.create_index(f"ix_council_assessments_{column}", "council_assessments", [column])


def downgrade() -> None:
    op.drop_table("council_assessments")
    op.drop_table("team_supervisors")
