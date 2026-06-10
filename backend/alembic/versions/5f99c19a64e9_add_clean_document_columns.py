"""add_clean_document_columns

Revision ID: 5f99c19a64e9
Revises: 0002_add_user_preferences
Create Date: 2026-06-08 11:17:02.513757

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f99c19a64e9'
down_revision: Union[str, Sequence[str], None] = '0002_add_user_preferences'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
