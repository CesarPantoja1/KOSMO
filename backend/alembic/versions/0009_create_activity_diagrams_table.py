"""create_activity_diagrams_table

Revision ID: 84ab07bdb13c
Revises: 0008_agent_sessions
Create Date: 2026-07-21 21:06:40.635894

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "84ab07bdb13c"
down_revision: str | Sequence[str] | None = "0008_agent_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "activity_diagrams",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("feature_id", sa.String(length=64), nullable=False),
        sa.Column("diagram_syntax", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["feature_id"], ["features.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_activity_diagrams_feature_id"), "activity_diagrams", ["feature_id"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_activity_diagrams_feature_id"), table_name="activity_diagrams")
    op.drop_table("activity_diagrams")
