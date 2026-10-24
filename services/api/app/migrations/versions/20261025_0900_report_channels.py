"""Accept every report channel the citizen app offers.

The Home screen starts reports by voice, text, photo or location. The intake
check allowed only text and voice, so photo- and location-started reports
were refused.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_reports_channel"), "reports", type_="check")
    op.create_check_constraint(
        op.f("ck_reports_channel"), "reports", "channel IN ('text','voice','photo','location')"
    )


def downgrade() -> None:
    # The older constraint cannot hold photo/location rows; keep them as text.
    op.execute("UPDATE reports SET channel = 'text' WHERE channel IN ('photo','location')")
    op.drop_constraint(op.f("ck_reports_channel"), "reports", type_="check")
    op.create_check_constraint(op.f("ck_reports_channel"), "reports", "channel IN ('text','voice')")
