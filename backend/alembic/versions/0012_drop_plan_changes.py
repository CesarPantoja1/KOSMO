"""eliminar tabla plan_changes

Revision ID: 0012_drop_plan_changes
Revises: 0011_chat_sessions
Create Date: 2026-08-14 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0012_drop_plan_changes"
down_revision: str | Sequence[str] | None = "0011_chat_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("plan_changes")


def downgrade() -> None:
    import sqlalchemy as sa

    op.create_table(
        "plan_changes",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("project_id", sa.String(64), nullable=False, index=True),
        sa.Column("phase", sa.String(32), nullable=False, index=True),
        sa.Column("context_id", sa.String(64), nullable=True),
        sa.Column("section", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("diff_before", sa.Text(), nullable=False),
        sa.Column("diff_after", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("origin", sa.String(64), nullable=False),
        sa.Column("user_version", sa.Text(), nullable=True),
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
