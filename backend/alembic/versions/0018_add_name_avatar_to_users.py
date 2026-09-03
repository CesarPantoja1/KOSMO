"""add name and avatar_url to users table

Revision ID: 0018_add_name_avatar_to_users
Revises: 0017_project_integrations
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0018_add_name_avatar_to_users"
down_revision: str | None = "0017_project_integrations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("name", sa.String(length=100), server_default="", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "name")
