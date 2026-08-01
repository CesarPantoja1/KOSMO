"""indice hnsw omitido: vector sin dimension fija en agent_sessions (no-op)

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
    pass


def downgrade() -> None:
    pass
