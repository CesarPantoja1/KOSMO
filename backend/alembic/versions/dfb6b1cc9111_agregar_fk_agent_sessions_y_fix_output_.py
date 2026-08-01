"""agregar indices compuestos knowledge_patterns y plan_changes

Revision ID: dfb6b1cc9111
Revises: bbc83814a1d6
Create Date: 2026-07-31

"""

from collections.abc import Sequence

from alembic import op


revision: str = "dfb6b1cc9111"
down_revision: str | Sequence[str] | None = "bbc83814a1d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_knowledge_patterns_phase_support",
        "knowledge_patterns",
        ["phase", "support_count"],
    )
    op.create_index(
        "ix_plan_changes_lookup",
        "plan_changes",
        ["project_id", "phase"],
    )


def downgrade() -> None:
    op.drop_index("ix_plan_changes_lookup", table_name="plan_changes")
    op.drop_index("ix_knowledge_patterns_phase_support", table_name="knowledge_patterns")
