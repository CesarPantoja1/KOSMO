"""remove_feature_status

Revision ID: f2f6de23e76e
Revises: 769f4fa2d80c
Create Date: 2026-06-13 22:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "f2f6de23e76e"
down_revision: str | None = "769f4fa2d80c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("features", "status")


def downgrade() -> None:
    pass
