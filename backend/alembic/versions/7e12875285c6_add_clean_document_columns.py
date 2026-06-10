"""add_clean_document_columns

Revision ID: 7e12875285c6
Revises: 5f99c19a64e9
Create Date: 2026-06-08 21:26:17.257191

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7e12875285c6'
down_revision: Union[str, Sequence[str], None] = '5f99c19a64e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("discovery_clean", sa.JSON(), nullable=True))
    op.add_column("features", sa.Column("requirements_clean", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("features", "requirements_clean")
    op.drop_column("projects", "discovery_clean")
