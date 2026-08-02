"""fijar_dimension_embedding_y_crear_indice_hnsw

Revision ID: 495f1e2ae4c7
Revises: dfb6b1cc9111
Create Date: 2026-08-01 20:07:20.270669

"""

from collections.abc import Sequence

from alembic import op

revision: str = "495f1e2ae4c7"
down_revision: str | Sequence[str] | None = "dfb6b1cc9111"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE agent_sessions ALTER COLUMN embedding TYPE vector(384) USING embedding::vector(384)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_agent_sessions_embedding_hnsw "
        "ON agent_sessions USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_agent_sessions_embedding_hnsw")
    op.execute("ALTER TABLE agent_sessions ALTER COLUMN embedding TYPE vector USING embedding::vector")
