"""crear tabla knowledge_patterns

Revision ID: 706a54cd4146
Revises: 075105f04aa4
Create Date: 2026-07-25 20:10:02.254868

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "706a54cd4146"
down_revision: str | Sequence[str] | None = "075105f04aa4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_patterns",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("phase", sa.String(32), nullable=False, index=True),
        sa.Column("pattern_text", sa.Text(), nullable=False),
        sa.Column("support_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("knowledge_patterns")
