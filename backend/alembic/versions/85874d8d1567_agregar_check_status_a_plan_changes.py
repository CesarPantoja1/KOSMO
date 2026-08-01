"""agregar check status a plan_changes

Revision ID: 85874d8d1567
Revises: 716792b913fe
Create Date: 2026-07-31 19:40:05.868041

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "85874d8d1567"
down_revision: str | Sequence[str] | None = "716792b913fe"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_VALID_STATUSES = ("pending", "added", "conflict", "applied", "discarded")


def upgrade() -> None:
    op.create_check_constraint(
        "ck_plan_changes_status",
        "plan_changes",
        sa.column("status").in_(_VALID_STATUSES),
    )


def downgrade() -> None:
    op.drop_constraint("ck_plan_changes_status", "plan_changes")
