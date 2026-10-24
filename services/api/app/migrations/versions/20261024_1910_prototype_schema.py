"""prototype schema

Revision ID: 0001
Revises:
Create Date: 2026-10-24 19:10:07.570735
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE report_code_seq AS bigint")
    op.create_table(
        "organizations",
        sa.Column("type", sa.String(length=24), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.CheckConstraint(
            "type IN ('district','department','institute','industry')",
            name=op.f("ck_organizations_type"),
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["organizations.id"],
            name=op.f("fk_organizations_parent_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
        sa.UniqueConstraint("code", name=op.f("uq_organizations_code")),
    )
    op.create_index(
        op.f("ix_organizations_parent_id"), "organizations", ["parent_id"], unique=False
    )
    op.create_table(
        "department_categories",
        sa.Column("department_id", sa.UUID(), nullable=False),
        sa.Column("district_id", sa.UUID(), nullable=False),
        sa.Column("category", sa.String(length=24), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.CheckConstraint(
            "category IN ('water', 'roads', 'lighting', 'sanitation', 'health', "
            "'education', 'electricity', 'transport', 'other')",
            name=op.f("ck_department_categories_category"),
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["organizations.id"],
            name=op.f("fk_department_categories_department_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["district_id"],
            ["organizations.id"],
            name=op.f("fk_department_categories_district_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_department_categories")),
        sa.UniqueConstraint(
            "district_id", "category", name=op.f("uq_department_categories_district_id_category")
        ),
    )
    op.create_index(
        op.f("ix_department_categories_department_id"),
        "department_categories",
        ["department_id"],
        unique=False,
    )
    op.create_table(
        "users",
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False),
        sa.Column("district_id", sa.UUID(), nullable=True),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column("institute_id", sa.UUID(), nullable=True),
        sa.Column("organization_id", sa.UUID(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.CheckConstraint(
            "role IN ('citizen','student','faculty','institute','panchayat','department',"
            "'officer','industry','gov_admin','super_admin')",
            name=op.f("ck_users_role"),
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["organizations.id"],
            name=op.f("fk_users_department_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["district_id"], ["organizations.id"], name=op.f("fk_users_district_id_organizations")
        ),
        sa.ForeignKeyConstraint(
            ["institute_id"], ["organizations.id"], name=op.f("fk_users_institute_id_organizations")
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_users_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("firebase_uid", name=op.f("uq_users_firebase_uid")),
    )
    op.create_index(op.f("ix_users_department_id"), "users", ["department_id"], unique=False)
    op.create_index(op.f("ix_users_district_id"), "users", ["district_id"], unique=False)
    op.create_index(op.f("ix_users_institute_id"), "users", ["institute_id"], unique=False)
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)
    op.create_table(
        "audit_events",
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("actor_role", sa.String(length=24), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("district_id", sa.UUID(), nullable=True),
        sa.Column(
            "before", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "after", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name=op.f("fk_audit_events_actor_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["district_id"],
            ["organizations.id"],
            name=op.f("fk_audit_events_district_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index(op.f("ix_audit_events_actor_id"), "audit_events", ["actor_id"], unique=False)
    op.create_index(
        "ix_audit_events_district_created",
        "audit_events",
        ["district_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "idempotency_keys",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("operation", sa.String(length=100), nullable=False),
        sa.Column("key", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column(
            "response_json",
            postgresql.JSONB(none_as_null=True, astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.CheckConstraint(
            "request_hash ~ '^[0-9a-f]{64}$'", name=op.f("ck_idempotency_keys_hash")
        ),
        sa.CheckConstraint(
            "(status_code IS NULL) = (response_json IS NULL)",
            name=op.f("ck_idempotency_keys_response_pair"),
        ),
        sa.CheckConstraint("length(trim(key)) > 0", name=op.f("ck_idempotency_keys_nonempty_key")),
        sa.CheckConstraint(
            "length(trim(operation)) > 0", name=op.f("ck_idempotency_keys_nonempty_operation")
        ),
        sa.CheckConstraint(
            "status_code BETWEEN 200 AND 299", name=op.f("ck_idempotency_keys_success_status")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_idempotency_keys_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_idempotency_keys")),
        sa.UniqueConstraint(
            "user_id", "operation", "key", name=op.f("uq_idempotency_keys_user_id_operation_key")
        ),
    )
    op.create_table(
        "reports",
        sa.Column(
            "code",
            sa.String(length=40),
            server_default=sa.text("'JM-' || nextval('report_code_seq')::text"),
            nullable=False,
        ),
        sa.Column("reporter_id", sa.UUID(), nullable=False),
        sa.Column("district_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=24), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "status_changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("location_label", sa.String(length=200), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("cluster_id", sa.UUID(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.CheckConstraint(
            "category IN ('water', 'roads', 'lighting', 'sanitation', 'health', "
            "'education', 'electricity', 'transport', 'other')",
            name=op.f("ck_reports_category"),
        ),
        sa.CheckConstraint("channel IN ('text','voice')", name=op.f("ck_reports_channel")),
        sa.CheckConstraint(
            "cluster_id IS NULL OR status = 'verified'",
            name=op.f("ck_reports_validated_membership"),
        ),
        sa.CheckConstraint(
            "severity IN ('low','medium','high','critical')", name=op.f("ck_reports_severity")
        ),
        sa.CheckConstraint(
            "status <> 'rejected' OR (rejection_reason IS NOT NULL "
            "AND length(trim(rejection_reason)) > 0)",
            name=op.f("ck_reports_rejection_reason"),
        ),
        sa.CheckConstraint(
            "status IN ('reported','verified','rejected')", name=op.f("ck_reports_intake_status")
        ),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name=op.f("ck_reports_latitude")),
        sa.CheckConstraint("longitude BETWEEN -180 AND 180", name=op.f("ck_reports_longitude")),
        sa.ForeignKeyConstraint(
            ["district_id"], ["organizations.id"], name=op.f("fk_reports_district_id_organizations")
        ),
        sa.ForeignKeyConstraint(
            ["reporter_id"], ["users.id"], name=op.f("fk_reports_reporter_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reports")),
        sa.UniqueConstraint("code", name=op.f("uq_reports_code")),
    )
    op.create_index(op.f("ix_reports_cluster_id"), "reports", ["cluster_id"], unique=False)
    op.create_index(op.f("ix_reports_district_id"), "reports", ["district_id"], unique=False)
    op.create_index(op.f("ix_reports_reporter_id"), "reports", ["reporter_id"], unique=False)
    op.create_table(
        "clusters",
        sa.Column("district_id", sa.UUID(), nullable=False),
        sa.Column("category", sa.String(length=24), nullable=False),
        sa.Column("anchor_report_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "status_changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("infrastructure_gap", sa.Float(), nullable=True),
        sa.Column("equity_index", sa.Float(), nullable=True),
        sa.Column("inputs_are_demo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.CheckConstraint(
            "category IN ('water', 'roads', 'lighting', 'sanitation', 'health', "
            "'education', 'electricity', 'transport', 'other')",
            name=op.f("ck_clusters_category"),
        ),
        sa.CheckConstraint(
            "status IN ('prioritised','funded','in_progress',"
            "'awaiting_verification','citizen_verified')",
            name=op.f("ck_clusters_execution_status"),
        ),
        sa.CheckConstraint("equity_index BETWEEN 0 AND 100", name=op.f("ck_clusters_equity_range")),
        sa.CheckConstraint(
            "infrastructure_gap BETWEEN 0 AND 100", name=op.f("ck_clusters_gap_range")
        ),
        sa.ForeignKeyConstraint(
            ["anchor_report_id"], ["reports.id"], name=op.f("fk_clusters_anchor_report_id_reports")
        ),
        sa.ForeignKeyConstraint(
            ["district_id"],
            ["organizations.id"],
            name=op.f("fk_clusters_district_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clusters")),
        sa.UniqueConstraint("anchor_report_id", name=op.f("uq_clusters_anchor_report_id")),
    )
    op.create_index(op.f("ix_clusters_district_id"), "clusters", ["district_id"], unique=False)
    # Reports must exist before the anchor FK; clusters must exist before this FK.
    op.create_foreign_key(
        "fk_reports_cluster_id_clusters", "reports", "clusters", ["cluster_id"], ["id"]
    )
    op.execute("ALTER SEQUENCE report_code_seq OWNED BY reports.code")
    op.create_table(
        "problem_statements",
        sa.Column("department_id", sa.UUID(), nullable=False),
        sa.Column("district_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("cluster_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.CheckConstraint(
            "status <> 'published' OR published_at IS NOT NULL",
            name=op.f("ck_problem_statements_publish_date"),
        ),
        sa.CheckConstraint(
            "status IN ('draft','published')", name=op.f("ck_problem_statements_status")
        ),
        sa.ForeignKeyConstraint(
            ["cluster_id"], ["clusters.id"], name=op.f("fk_problem_statements_cluster_id_clusters")
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_problem_statements_created_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["organizations.id"],
            name=op.f("fk_problem_statements_department_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["district_id"],
            ["organizations.id"],
            name=op.f("fk_problem_statements_district_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_problem_statements")),
    )
    op.create_index(
        op.f("ix_problem_statements_cluster_id"), "problem_statements", ["cluster_id"], unique=False
    )
    op.create_index(
        op.f("ix_problem_statements_department_id"),
        "problem_statements",
        ["department_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_problem_statements_district_id"),
        "problem_statements",
        ["district_id"],
        unique=False,
    )
    op.create_table(
        "supports",
        sa.Column("cluster_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["cluster_id"], ["clusters.id"], name=op.f("fk_supports_cluster_id_clusters")
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_supports_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_supports")),
        sa.UniqueConstraint("cluster_id", "user_id", name=op.f("uq_supports_cluster_id_user_id")),
    )
    op.create_index(op.f("ix_supports_user_id"), "supports", ["user_id"], unique=False)
    op.create_table(
        "work_orders",
        sa.Column("cluster_id", sa.UUID(), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=False),
        sa.Column("district_id", sa.UUID(), nullable=False),
        sa.Column("officer_id", sa.UUID(), nullable=False),
        sa.Column("round", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        sa.Column("instructions", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.CheckConstraint("round >= 1", name=op.f("ck_work_orders_positive_round")),
        sa.ForeignKeyConstraint(
            ["cluster_id"], ["clusters.id"], name=op.f("fk_work_orders_cluster_id_clusters")
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["organizations.id"],
            name=op.f("fk_work_orders_department_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["district_id"],
            ["organizations.id"],
            name=op.f("fk_work_orders_district_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["officer_id"], ["users.id"], name=op.f("fk_work_orders_officer_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_work_orders")),
        sa.UniqueConstraint("cluster_id", name=op.f("uq_work_orders_cluster_id")),
    )
    op.create_index(
        op.f("ix_work_orders_department_id"), "work_orders", ["department_id"], unique=False
    )
    op.create_index(
        op.f("ix_work_orders_district_id"), "work_orders", ["district_id"], unique=False
    )
    op.create_index(op.f("ix_work_orders_officer_id"), "work_orders", ["officer_id"], unique=False)
    op.create_table(
        "allocations",
        sa.Column("cluster_id", sa.UUID(), nullable=False),
        sa.Column("work_order_id", sa.UUID(), nullable=False),
        sa.Column("amount_paise", sa.BigInteger(), nullable=False),
        sa.Column("allocated_by", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.CheckConstraint("amount_paise > 0", name=op.f("ck_allocations_positive_amount")),
        sa.ForeignKeyConstraint(
            ["allocated_by"], ["users.id"], name=op.f("fk_allocations_allocated_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["cluster_id"], ["clusters.id"], name=op.f("fk_allocations_cluster_id_clusters")
        ),
        sa.ForeignKeyConstraint(
            ["work_order_id"],
            ["work_orders.id"],
            name=op.f("fk_allocations_work_order_id_work_orders"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_allocations")),
        sa.UniqueConstraint("cluster_id", name=op.f("uq_allocations_cluster_id")),
        sa.UniqueConstraint("work_order_id", name=op.f("uq_allocations_work_order_id")),
    )
    op.create_table(
        "media_assets",
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("public_id", sa.String(length=255), nullable=False),
        sa.Column("asset_id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("format", sa.String(length=8), nullable=False),
        sa.Column("bytes", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("report_id", sa.UUID(), nullable=True),
        sa.Column("work_order_id", sa.UUID(), nullable=True),
        sa.Column("round", sa.Integer(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.CheckConstraint(
            "(kind = 'report' AND work_order_id IS NULL AND round IS NULL) OR "
            "(kind = 'completion' AND report_id IS NULL AND "
            "((work_order_id IS NULL AND round IS NULL) OR "
            "(work_order_id IS NOT NULL AND round IS NOT NULL AND round >= 1)))",
            name=op.f("ck_media_assets_attachment_kind_and_round"),
        ),
        sa.CheckConstraint(
            "format IN ('jpg','jpeg','png','webp')", name=op.f("ck_media_assets_format")
        ),
        sa.CheckConstraint("kind IN ('report','completion')", name=op.f("ck_media_assets_kind")),
        sa.CheckConstraint(
            "bytes > 0 AND bytes <= 10485760", name=op.f("ck_media_assets_byte_limit")
        ),
        sa.CheckConstraint("version > 0", name=op.f("ck_media_assets_version")),
        sa.CheckConstraint("width > 0 AND height > 0", name=op.f("ck_media_assets_dimensions")),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_media_assets_owner_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["report_id"], ["reports.id"], name=op.f("fk_media_assets_report_id_reports")
        ),
        sa.ForeignKeyConstraint(
            ["work_order_id"],
            ["work_orders.id"],
            name=op.f("fk_media_assets_work_order_id_work_orders"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_assets")),
        sa.UniqueConstraint("asset_id", name=op.f("uq_media_assets_asset_id")),
        sa.UniqueConstraint("public_id", name=op.f("uq_media_assets_public_id")),
    )
    op.create_index(op.f("ix_media_assets_owner_id"), "media_assets", ["owner_id"], unique=False)
    op.create_index(op.f("ix_media_assets_report_id"), "media_assets", ["report_id"], unique=False)
    op.create_index(
        op.f("ix_media_assets_work_order_id"), "media_assets", ["work_order_id"], unique=False
    )
    op.create_table(
        "sponsorships",
        sa.Column("statement_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("pledged_by", sa.UUID(), nullable=False),
        sa.Column("amount_paise", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pledged", nullable=False),
        sa.Column(
            "pledged_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.CheckConstraint("status = 'pledged'", name=op.f("ck_sponsorships_pledge_only")),
        sa.CheckConstraint("amount_paise > 0", name=op.f("ck_sponsorships_positive_amount")),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_sponsorships_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["pledged_by"], ["users.id"], name=op.f("fk_sponsorships_pledged_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["statement_id"],
            ["problem_statements.id"],
            name=op.f("fk_sponsorships_statement_id_problem_statements"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sponsorships")),
    )
    op.create_index(
        op.f("ix_sponsorships_organization_id"), "sponsorships", ["organization_id"], unique=False
    )
    op.create_index(
        op.f("ix_sponsorships_statement_id"), "sponsorships", ["statement_id"], unique=False
    )
    op.create_table(
        "teams",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("institute_id", sa.UUID(), nullable=False),
        sa.Column("statement_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column(
            "institute_approved", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.CheckConstraint(
            "NOT institute_approved OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)",
            name=op.f("ck_teams_approval_evidence"),
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"], ["users.id"], name=op.f("fk_teams_approved_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_teams_created_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["institute_id"], ["organizations.id"], name=op.f("fk_teams_institute_id_organizations")
        ),
        sa.ForeignKeyConstraint(
            ["statement_id"],
            ["problem_statements.id"],
            name=op.f("fk_teams_statement_id_problem_statements"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teams")),
    )
    op.create_index(op.f("ix_teams_created_by"), "teams", ["created_by"], unique=False)
    op.create_index(op.f("ix_teams_institute_id"), "teams", ["institute_id"], unique=False)
    op.create_index(op.f("ix_teams_statement_id"), "teams", ["statement_id"], unique=False)
    op.create_table(
        "verifications",
        sa.Column("work_order_id", sa.UUID(), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("citizen_id", sa.UUID(), nullable=False),
        sa.Column("verdict", sa.Boolean(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.CheckConstraint("length(comment) <= 500", name=op.f("ck_verifications_comment_length")),
        sa.CheckConstraint("round >= 1", name=op.f("ck_verifications_positive_round")),
        sa.ForeignKeyConstraint(
            ["citizen_id"], ["users.id"], name=op.f("fk_verifications_citizen_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["work_order_id"],
            ["work_orders.id"],
            name=op.f("fk_verifications_work_order_id_work_orders"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_verifications")),
        sa.UniqueConstraint(
            "work_order_id", "round", name=op.f("uq_verifications_work_order_id_round")
        ),
    )
    op.create_index(
        op.f("ix_verifications_citizen_id"), "verifications", ["citizen_id"], unique=False
    )
    op.create_table(
        "submissions",
        sa.Column("team_id", sa.UUID(), nullable=False),
        sa.Column("statement_id", sa.UUID(), nullable=False),
        sa.Column("submitted_by", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("link", sa.String(length=2048), nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.CheckConstraint(
            "link IS NULL OR link ~ '^https://[^/[:space:]]+'",
            name=op.f("ck_submissions_https_link"),
        ),
        sa.ForeignKeyConstraint(
            ["statement_id"],
            ["problem_statements.id"],
            name=op.f("fk_submissions_statement_id_problem_statements"),
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by"], ["users.id"], name=op.f("fk_submissions_submitted_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["team_id"], ["teams.id"], name=op.f("fk_submissions_team_id_teams")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_submissions")),
    )
    op.create_index(
        op.f("ix_submissions_statement_id"), "submissions", ["statement_id"], unique=False
    )
    op.create_index(op.f("ix_submissions_team_id"), "submissions", ["team_id"], unique=False)
    op.create_table(
        "team_members",
        sa.Column("team_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["team_id"], ["teams.id"], name=op.f("fk_team_members_team_id_teams")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_team_members_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_team_members")),
        sa.UniqueConstraint("team_id", "user_id", name=op.f("uq_team_members_team_id_user_id")),
    )
    op.create_index(op.f("ix_team_members_user_id"), "team_members", ["user_id"], unique=False)
    op.create_table(
        "reviews",
        sa.Column("submission_id", sa.UUID(), nullable=False),
        sa.Column("reviewer_id", sa.UUID(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.CheckConstraint("score BETWEEN 1 AND 5", name=op.f("ck_reviews_score_range")),
        sa.ForeignKeyConstraint(
            ["reviewer_id"], ["users.id"], name=op.f("fk_reviews_reviewer_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"], ["submissions.id"], name=op.f("fk_reviews_submission_id_submissions")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reviews")),
        sa.UniqueConstraint(
            "submission_id", "reviewer_id", name=op.f("uq_reviews_submission_id_reviewer_id")
        ),
    )
    op.create_index(op.f("ix_reviews_reviewer_id"), "reviews", ["reviewer_id"], unique=False)


def downgrade() -> None:
    op.drop_constraint("fk_reports_cluster_id_clusters", "reports", type_="foreignkey")
    op.drop_index(op.f("ix_reviews_reviewer_id"), table_name="reviews")
    op.drop_table("reviews")
    op.drop_index(op.f("ix_team_members_user_id"), table_name="team_members")
    op.drop_table("team_members")
    op.drop_index(op.f("ix_submissions_team_id"), table_name="submissions")
    op.drop_index(op.f("ix_submissions_statement_id"), table_name="submissions")
    op.drop_table("submissions")
    op.drop_index(op.f("ix_verifications_citizen_id"), table_name="verifications")
    op.drop_table("verifications")
    op.drop_index(op.f("ix_teams_statement_id"), table_name="teams")
    op.drop_index(op.f("ix_teams_institute_id"), table_name="teams")
    op.drop_index(op.f("ix_teams_created_by"), table_name="teams")
    op.drop_table("teams")
    op.drop_index(op.f("ix_sponsorships_statement_id"), table_name="sponsorships")
    op.drop_index(op.f("ix_sponsorships_organization_id"), table_name="sponsorships")
    op.drop_table("sponsorships")
    op.drop_index(op.f("ix_media_assets_work_order_id"), table_name="media_assets")
    op.drop_index(op.f("ix_media_assets_report_id"), table_name="media_assets")
    op.drop_index(op.f("ix_media_assets_owner_id"), table_name="media_assets")
    op.drop_table("media_assets")
    op.drop_table("allocations")
    op.drop_index(op.f("ix_work_orders_officer_id"), table_name="work_orders")
    op.drop_index(op.f("ix_work_orders_district_id"), table_name="work_orders")
    op.drop_index(op.f("ix_work_orders_department_id"), table_name="work_orders")
    op.drop_table("work_orders")
    op.drop_index(op.f("ix_supports_user_id"), table_name="supports")
    op.drop_table("supports")
    op.drop_index(op.f("ix_problem_statements_district_id"), table_name="problem_statements")
    op.drop_index(op.f("ix_problem_statements_department_id"), table_name="problem_statements")
    op.drop_index(op.f("ix_problem_statements_cluster_id"), table_name="problem_statements")
    op.drop_table("problem_statements")
    op.drop_index(op.f("ix_clusters_district_id"), table_name="clusters")
    op.drop_table("clusters")
    op.drop_index(op.f("ix_reports_reporter_id"), table_name="reports")
    op.drop_index(op.f("ix_reports_district_id"), table_name="reports")
    op.drop_index(op.f("ix_reports_cluster_id"), table_name="reports")
    op.drop_table("reports")
    op.drop_table("idempotency_keys")
    op.drop_index("ix_audit_events_district_created", table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_actor_id"), table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_index(op.f("ix_users_institute_id"), table_name="users")
    op.drop_index(op.f("ix_users_district_id"), table_name="users")
    op.drop_index(op.f("ix_users_department_id"), table_name="users")
    op.drop_table("users")
    op.drop_index(
        op.f("ix_department_categories_department_id"), table_name="department_categories"
    )
    op.drop_table("department_categories")
    op.drop_index(op.f("ix_organizations_parent_id"), table_name="organizations")
    op.drop_table("organizations")
