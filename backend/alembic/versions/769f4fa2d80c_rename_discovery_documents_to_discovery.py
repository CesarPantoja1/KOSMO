"""rename_discovery_documents_to_discovery

Revision ID: 769f4fa2d80c
Revises: 5b5161b3a623
Create Date: 2026-06-13 20:45:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "769f4fa2d80c"
down_revision: str | None = "5b5161b3a623"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.rename_table("discovery_documents", "discovery")


def downgrade() -> None:
    op.rename_table("discovery", "discovery_documents")
