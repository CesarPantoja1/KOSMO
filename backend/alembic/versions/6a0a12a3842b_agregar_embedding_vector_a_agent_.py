"""agregar embedding y reflection a agent_sessions

Revision ID: 6a0a12a3842b
Revises: 84ab07bdb13c
Create Date: 2026-07-25 16:47:19.533170

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision: str = "6a0a12a3842b"
down_revision: str | Sequence[str] | None = "84ab07bdb13c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column(
        "agent_sessions",
        sa.Column("embedding", Vector(1536), nullable=True),
    )
    op.add_column(
        "agent_sessions",
        sa.Column("reflection", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent_sessions", "reflection")
    op.drop_column("agent_sessions", "embedding")
