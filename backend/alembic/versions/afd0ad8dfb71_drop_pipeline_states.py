"""drop_pipeline_states

Revision ID: afd0ad8dfb71
Revises: e5e0bda961df
Create Date: 2026-06-13 23:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "afd0ad8dfb71"
down_revision: str | None = "e5e0bda961df"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("pipeline_states")


def downgrade() -> None:
    pass
