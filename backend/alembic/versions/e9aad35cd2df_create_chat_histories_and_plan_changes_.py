"""create chat_histories and plan_changes tables

Revision ID: e9aad35cd2df
Revises: 706a54cd4146
Create Date: 2026-07-29 14:41:26.399131

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op

revision: str = "e9aad35cd2df"
down_revision: str | Sequence[str] | None = "706a54cd4146"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_histories",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("project_id", sa.String(64), nullable=False, index=True),
        sa.Column("phase", sa.String(32), nullable=False, index=True),
        sa.Column("context_id", sa.String(64), nullable=True),
        sa.Column("messages", pg.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "plan_changes",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("project_id", sa.String(64), nullable=False, index=True),
        sa.Column("phase", sa.String(32), nullable=False, index=True),
        sa.Column("context_id", sa.String(64), nullable=True),
        sa.Column("section", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("diff_before", sa.Text(), nullable=False),
        sa.Column("diff_after", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("origin", sa.String(64), nullable=False),
        sa.Column("user_version", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("plan_changes")
    op.drop_table("chat_histories")
