"""simplify_requirements_move_blob

Revision ID: db75f0b14dc8
Revises: afd0ad8dfb71
Create Date: 2026-06-14 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "db75f0b14dc8"
down_revision: str | None = "afd0ad8dfb71"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS requirements CASCADE")

    op.create_table(
        "requirements",
        sa.Column("feature_id", sa.String(64), primary_key=True, nullable=False),
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
        "fk_requirements_feature",
        "requirements",
        "features",
        ["feature_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_column("features", "requirements_document")


def downgrade() -> None:
    pass
