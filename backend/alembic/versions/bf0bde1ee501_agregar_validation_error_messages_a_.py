"""agregar validation_error_messages a agent_sessions

Revision ID: bf0bde1ee501
Revises: 6a0a12a3842b
Create Date: 2026-07-25 18:55:11.231913

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "bf0bde1ee501"
down_revision: str | Sequence[str] | None = "6a0a12a3842b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_sessions",
        sa.Column(
            "validation_error_messages",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("agent_sessions", "validation_error_messages")
