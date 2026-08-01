"""crear tabla document_versions para historial de cambios

Revision ID: 5542189c7575
Revises: 276a31b1b4c2
Create Date: 2026-07-31

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op

revision: str = "5542189c7575"
down_revision: str | Sequence[str] | None = "276a31b1b4c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_versions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("project_id", sa.String(64), nullable=False, index=True),
        sa.Column("phase", sa.String(32), nullable=False),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("change_ids", pg.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_document_versions_lookup",
        "document_versions",
        ["project_id", "phase", "created_at"],
    )
    op.create_foreign_key(
        "fk_document_versions_project",
        "document_versions",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_table("document_versions")
