"""eliminar_tabla_async_jobs

Revision ID: ed1e31519d67
Revises: c93e06e1f3ae
Create Date: 2026-08-01 23:51:27.046225

"""

from collections.abc import Sequence

from alembic import op

revision: str = "ed1e31519d67"
down_revision: str | Sequence[str] | None = "c93e06e1f3ae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("async_jobs")


def downgrade() -> None:
    pass
