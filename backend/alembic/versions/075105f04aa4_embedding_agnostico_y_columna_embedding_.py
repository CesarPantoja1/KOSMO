"""embedding agnostico y columna embedding_model

Revision ID: 075105f04aa4
Revises: bf0bde1ee501
Create Date: 2026-07-25 19:06:47.606018

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "075105f04aa4"
down_revision: str | Sequence[str] | None = "bf0bde1ee501"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE agent_sessions ALTER COLUMN embedding TYPE vector USING embedding::vector")
    op.add_column(
        "agent_sessions",
        sa.Column("embedding_model", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent_sessions", "embedding_model")
    op.execute("ALTER TABLE agent_sessions ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536)")
