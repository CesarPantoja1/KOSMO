"""agregar indice hnsw en agent_sessions embedding

Revision ID: 4d1f8392bd76
Revises: d9eb81634a75
Create Date: 2026-07-31

"""

from collections.abc import Sequence

from alembic import op

revision: str = "4d1f8392bd76"
down_revision: str | Sequence[str] | None = "d9eb81634a75"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_agent_sessions_embedding_hnsw "
        "ON agent_sessions USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.drop_index("ix_agent_sessions_embedding_hnsw", table_name="agent_sessions")
