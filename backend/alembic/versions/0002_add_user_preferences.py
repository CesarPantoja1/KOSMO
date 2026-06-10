"""add_user_preferences

Revision ID: 0002_add_user_preferences
Revises: 0001_init
Create Date: 2026-06-07 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_add_user_preferences"
down_revision: str | Sequence[str] | None = "0001_init"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_preferences",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=32), nullable=True),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("rule_text", sa.Text(), nullable=False),
        sa.Column("context_snippet", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "corpus",
            sa.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
            server_default=sa.text("1.0"),
        ),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_user_preferences_user_id", "user_preferences", ["user_id"])
    op.create_index(
        "idx_user_preferences_user_project",
        "user_preferences",
        ["user_id", "project_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_user_preferences_user_project", table_name="user_preferences")
    op.drop_index("idx_user_preferences_user_id", table_name="user_preferences")
    op.drop_table("user_preferences")
