"""reemplazar chat_histories por chat_messages append-only

Revision ID: d9eb81634a75
Revises: 85874d8d1567
Create Date: 2026-07-31

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op

revision: str = "d9eb81634a75"
down_revision: str | Sequence[str] | None = "85874d8d1567"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("chat_histories")

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("project_id", sa.String(64), nullable=False, index=True),
        sa.Column("phase", sa.String(32), nullable=False),
        sa.Column("context_id", sa.String(64), nullable=True),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("suggested_change", pg.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_chat_messages_lookup",
        "chat_messages",
        ["project_id", "phase", "context_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("chat_messages")

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
