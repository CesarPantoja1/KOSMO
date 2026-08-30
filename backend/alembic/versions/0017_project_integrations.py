"""create project_integrations and code_sync_logs tables

Revision ID: 0017_project_integrations
Revises: 0016_user_integrations
Create Date: 2026-08-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0017_project_integrations"
down_revision: str | None = "0016_user_integrations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_integrations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=32), server_default="github", nullable=False),
        sa.Column("repo_name", sa.String(length=255), nullable=True),
        sa.Column("repo_url", sa.String(length=512), nullable=True),
        sa.Column("is_public", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("default_branch", sa.String(length=100), server_default="main", nullable=False),
        sa.Column("last_push_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_commit_hash", sa.String(length=64), nullable=True),
        sa.Column("sync_status", sa.String(length=32), server_default="not_created", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "provider", name="uq_project_integrations_project_provider"),
    )
    op.create_index(op.f("ix_project_integrations_project_id"), "project_integrations", ["project_id"], unique=False)

    op.create_table(
        "code_sync_logs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("commit_sha", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="failed", nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_code_sync_logs_project_id"), "code_sync_logs", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_code_sync_logs_project_id"), table_name="code_sync_logs")
    op.drop_table("code_sync_logs")
    op.drop_index(op.f("ix_project_integrations_project_id"), table_name="project_integrations")
    op.drop_table("project_integrations")
