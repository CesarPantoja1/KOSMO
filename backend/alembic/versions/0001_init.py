"""KOSMO initial schema with ULID-based typed prefixed IDs

Revision ID: 0001_init
Revises: None
Create Date: 2026-05-31 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_init"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("hashed_password", sa.String(length=512), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("actor_id", sa.String(length=32), nullable=True),
        sa.Column("actor_email", sa.String(length=320), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("resource_type", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.String(length=128), nullable=True),
        sa.Column("payload", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("metadata", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("current_phase", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("discovery_document", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "constitutions",
        sa.Column("project_id", sa.String(length=32), nullable=False),
        sa.Column("product", sa.Text(), nullable=False),
        sa.Column("tech", sa.Text(), nullable=False),
        sa.Column("structure", sa.Text(), nullable=False),
        sa.Column("custom_data", sa.JSON(), nullable=True),
        sa.Column("version_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("project_id"),
    )

    op.create_table(
        "encrypted_api_keys",
        sa.Column("key_id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("cipher_text", sa.Text(), nullable=False),
        sa.Column("model_default", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key_id"),
    )
    op.create_index("ix_api_keys_user_id", "encrypted_api_keys", ["user_id"], unique=False)

    op.create_table(
        "pipeline_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(length=32), unique=True),
        sa.Column("spec_id", sa.String(length=32), index=True),
        sa.Column("event_type", sa.String(length=64)),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "specs",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("project_id", sa.String(length=32), nullable=False),
        sa.Column("phase", sa.String(length=32), nullable=False),
        sa.Column("discovery_data", sa.JSON(), nullable=True),
        sa.Column("roadmap_data", sa.JSON(), nullable=True),
        sa.Column("design_data", sa.JSON(), nullable=True),
        sa.Column("constitution_data", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_specs_project_id", "specs", ["project_id"], unique=False)

    op.create_table(
        "features",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("project_id", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("requirements_data", sa.JSON(), nullable=True),
        sa.Column("requirements_document", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_features_project_id", "features", ["project_id"], unique=False)

    op.create_table(
        "requirements",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("spec_id", sa.String(length=32), nullable=False),
        sa.Column("pattern", sa.String(length=32), nullable=False),
        sa.Column("trigger", sa.Text(), nullable=True),
        sa.Column("system", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=False),
        sa.Column("acceptance_criteria", sa.JSON(), nullable=True),
        sa.Column("source_statement", sa.Text(), nullable=False),
        sa.Column("traceability", sa.JSON(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.ForeignKeyConstraint(["spec_id"], ["specs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_requirements_spec_id", "requirements", ["spec_id"], unique=False)

    op.create_table(
        "tasks",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("spec_id", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("boundary", sa.String(length=128), nullable=False),
        sa.Column("depends_on", sa.JSON(), nullable=True),
        sa.Column("requirements", sa.JSON(), nullable=True),
        sa.Column("acceptance_criteria", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("parallelizable", sa.Boolean(), nullable=False),
        sa.Column("implementation_notes", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["spec_id"], ["specs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_spec_id", "tasks", ["spec_id"], unique=False)

    op.create_table(
        "artifacts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("spec_id", sa.String(length=32), index=True),
        sa.Column("kind", sa.String(length=64)),
        sa.Column("blob_key", sa.String(length=256)),
        sa.Column("content_sha256", sa.String(length=64)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("artifacts")
    op.drop_table("tasks")
    op.drop_table("requirements")
    op.drop_table("features")
    op.drop_table("specs")
    op.drop_table("pipeline_events")
    op.drop_table("encrypted_api_keys")
    op.drop_table("constitutions")
    op.drop_table("projects")
    op.drop_table("audit_log")
    op.drop_table("users")
