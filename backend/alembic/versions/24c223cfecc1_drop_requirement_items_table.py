"""drop requirement_items table

Revision ID: 24c223cfecc1
Revises: 99ffc4fbdb91
Create Date: 2026-08-05 21:52:51.556360

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "24c223cfecc1"
down_revision: str | Sequence[str] | None = "99ffc4fbdb91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("requirement_items")


def downgrade() -> None:
    op.create_table(
        "requirement_items",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("feature_id", sa.String(64), nullable=False, index=True),
        sa.Column("requirement_number", sa.Integer(), nullable=False),
        sa.Column("display_id", sa.String(16), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("pattern", sa.String(32), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("origin", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "acceptance_criteria", sa.JSON(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
