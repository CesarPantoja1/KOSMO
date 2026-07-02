"""replace rationale inferred_from with origin in features

Revision ID: 03852067b32c
Revises: 0007_fk_constraints
Create Date: 2026-07-02 09:47:29.188428

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "03852067b32c"
down_revision: str | Sequence[str] | None = "0007_fk_constraints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Reemplaza rationale + inferred_from por origin en features."""
    op.add_column("features", sa.Column("origin", sa.Text(), nullable=False, server_default=""))
    op.drop_column("features", "rationale")
    op.drop_column("features", "inferred_from")


def downgrade() -> None:
    """Restaura rationale + inferred_from en features."""
    op.add_column(
        "features",
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "features",
        sa.Column(
            "inferred_from",
            sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.drop_column("features", "origin")
