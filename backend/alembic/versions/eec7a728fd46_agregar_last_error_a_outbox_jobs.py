"""agregar_last_error_a_outbox_jobs

Revision ID: eec7a728fd46
Revises: c93e06e1f3ae
Create Date: 2026-08-01

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "eec7a728fd46"
down_revision: str | Sequence[str] | None = "c93e06e1f3ae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("outbox_jobs", sa.Column("last_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("outbox_jobs", "last_error")
