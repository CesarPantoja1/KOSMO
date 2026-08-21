"""agregar operation_id a consistency_evaluations

Revision ID: 0013_consistency_operation_id
Revises: 0012_drop_plan_changes
Create Date: 2026-08-15 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0013_consistency_operation_id"
down_revision: str | Sequence[str] | None = "0012_drop_plan_changes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "consistency_evaluations",
        sa.Column("operation_id", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("consistency_evaluations", "operation_id")
