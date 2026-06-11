"""replace_discovery_clean_with_md

Revision ID: 0003
Revises: 7e12875285c6
Create Date: 2026-06-11 20:00:00.000000

DiscoveryDocument structured fields are replaced by canonical Markdown text.
- Drops projects.discovery_clean (JSON)
- Adds projects.discovery_md (Text)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '7e12875285c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("projects", "discovery_clean")
    op.add_column("projects", sa.Column("discovery_md", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "discovery_md")
    op.add_column("projects", sa.Column("discovery_clean", sa.JSON(), nullable=True))
