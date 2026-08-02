"""merge async_jobs cleanup con outbox_jobs

Revision ID: b3a40a8da1d6
Revises: ed1e31519d67, eec7a728fd46
Create Date: 2026-08-02 14:25:19.621751

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3a40a8da1d6'
down_revision: Union[str, Sequence[str], None] = ('ed1e31519d67', 'eec7a728fd46')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
