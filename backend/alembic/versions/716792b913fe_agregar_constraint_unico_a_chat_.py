"""agregar constraint unico a chat_histories

Revision ID: 716792b913fe
Revises: e9aad35cd2df
Create Date: 2026-07-31 19:36:03.638362

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "716792b913fe"
down_revision: str | Sequence[str] | None = "e9aad35cd2df"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    dedup = sa.text("""
        DELETE FROM chat_histories
        WHERE id NOT IN (
            SELECT DISTINCT ON (project_id, phase, COALESCE(context_id, ''))
                id
            FROM chat_histories
            ORDER BY project_id, phase, COALESCE(context_id, ''), updated_at DESC
        )
    """)
    op.execute(dedup)

    op.create_index(
        "uq_chat_histories_project_phase_ctx",
        "chat_histories",
        ["project_id", "phase", "context_id"],
        unique=True,
        postgresql_where=sa.text("context_id IS NOT NULL"),
    )
    op.create_index(
        "uq_chat_histories_project_phase_null",
        "chat_histories",
        ["project_id", "phase"],
        unique=True,
        postgresql_where=sa.text("context_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_chat_histories_project_phase_ctx")
    op.drop_index("uq_chat_histories_project_phase_null")
