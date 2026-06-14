"""add_slug_to_projects

Revision ID: e5e0bda961df
Revises: f2f6de23e76e
Create Date: 2026-06-13 22:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5e0bda961df"
down_revision: str | None = "f2f6de23e76e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("slug", sa.String(255), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("projects", "slug")
