"""normalizar requisitos en filas y crear grafo de trazabilidad

Revision ID: 9d632f3bb0e4
Revises: 5542189c7575
Create Date: 2026-07-31

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op

revision: str = "9d632f3bb0e4"
down_revision: str | Sequence[str] | None = "5542189c7575"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "requirement_items",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("feature_id", sa.String(64), nullable=False, index=True),
        sa.Column("requirement_number", sa.Integer(), nullable=False),
        sa.Column("display_id", sa.String(16), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("pattern", sa.String(32), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("origin", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("acceptance_criteria", pg.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_requirement_items_feature_number",
        "requirement_items",
        ["feature_id", "requirement_number"],
        unique=True,
    )
    op.create_foreign_key(
        "fk_requirement_items_feature",
        "requirement_items",
        "features",
        ["feature_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_table(
        "traceability_edges",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_id", sa.String(64), nullable=False),
        sa.Column("target_type", sa.String(32), nullable=False),
        sa.Column("target_id", sa.String(64), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False, server_default=sa.text("'llm'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_traceability_edges_source",
        "traceability_edges",
        ["source_type", "source_id"],
    )
    op.create_index(
        "ix_traceability_edges_target",
        "traceability_edges",
        ["target_type", "target_id"],
    )


def downgrade() -> None:
    op.drop_table("traceability_edges")
    op.drop_table("requirement_items")
