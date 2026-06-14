"""add_discovery_documents_table

Revision ID: 9313ffd42cf9
Revises: 0002_pipeline_sdd
Create Date: 2026-06-13 19:57:06.238502

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9313ffd42cf9"
down_revision: str | None = "0002_pipeline_sdd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discovery_documents",
        sa.Column("project_id", sa.String(64), primary_key=True, nullable=False),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_foreign_key(
        "fk_discovery_documents_project",
        "discovery_documents",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.execute("DELETE FROM pipeline_states")


def downgrade() -> None:
    op.drop_table("discovery_documents")
