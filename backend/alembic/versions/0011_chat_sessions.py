"""crear tabla chat_sessions y asociar mensajes con session_id

Revision ID: 0011_chat_sessions
Revises: 0010_consistency_evaluations
Create Date: 2026-08-14 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011_chat_sessions"
down_revision: str | Sequence[str] | None = "0010_consistency_evaluations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("project_id", sa.String(64), nullable=False, index=True),
        sa.Column("phase", sa.String(32), nullable=False),
        sa.Column("context_id", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.add_column("chat_messages", sa.Column("session_id", sa.String(64), nullable=True))
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])

    # Backfill: una sesión "legacy" determinística por (project, phase, context)
    op.execute(
        """
        INSERT INTO chat_sessions (id, project_id, phase, context_id, created_at)
        SELECT
            'cht_' || substr(
                encode(digest(project_id || ':' || phase || ':' || COALESCE(context_id, ''), 'sha256'), 'hex'),
                1,
                60
            ),
            project_id,
            phase,
            context_id,
            MIN(created_at)
        FROM chat_messages
        GROUP BY project_id, phase, context_id
        ON CONFLICT (id) DO NOTHING
        """
    )
    op.execute(
        """
        UPDATE chat_messages AS m
        SET session_id = s.id
        FROM chat_sessions AS s
        WHERE s.project_id = m.project_id
          AND s.phase = m.phase
          AND COALESCE(s.context_id, '') = COALESCE(m.context_id, '')
        """
    )


def downgrade() -> None:
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_column("chat_messages", "session_id")
    op.drop_table("chat_sessions")
