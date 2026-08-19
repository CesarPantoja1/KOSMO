"""create workspaces and feature_implementations tables

Revision ID: 0014_workspaces_and_feature_implementations
Revises: 0013_consistency_operation_id
Create Date: 2026-08-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0014_workspaces_and_feature_implementations"
down_revision: str | None = "0013_consistency_operation_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("current_branch", sa.String(length=255), nullable=False),
        sa.Column("is_locked", sa.Boolean(), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=64), nullable=True),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workspaces_project_id"), "workspaces", ["project_id"], unique=False)

    op.create_table(
        "feature_implementations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("feature_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("branch", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_step", sa.String(length=32), nullable=False),
        sa.Column("iteration", sa.Integer(), nullable=False),
        sa.Column("plan", postgresql.JSONB(), nullable=True),
        sa.Column(
            "validation_results",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["feature_id"], ["features.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_feature_implementations_feature_id"),
        "feature_implementations",
        ["feature_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_feature_implementations_project_id"),
        "feature_implementations",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_feature_implementations_project_id"), table_name="feature_implementations")
    op.drop_index(op.f("ix_feature_implementations_feature_id"), table_name="feature_implementations")
    op.drop_table("feature_implementations")
    op.drop_index(op.f("ix_workspaces_project_id"), table_name="workspaces")
    op.drop_table("workspaces")
