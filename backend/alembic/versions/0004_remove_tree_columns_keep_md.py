"""remove_tree_columns_keep_md

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-11 22:00:00.000000

Elimina el arbol ProseMirror y los campos derivados. El Markdown es la unica fuente de verdad.
- Drops projects.discovery_document (JSON tree)
- Drops specs.discovery_data (JSON copy of DiscoveryDocument)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("projects", "discovery_document")
    op.drop_column("specs", "discovery_data")


def downgrade() -> None:
    op.add_column("projects", sa.Column("discovery_document", sa.JSON(), nullable=True))
    op.add_column("specs", sa.Column("discovery_data", sa.JSON(), nullable=True))
