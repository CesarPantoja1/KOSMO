"""create agent_sessions table for agent memory persistence

Revision ID: 0008_agent_sessions
Revises: 03852067b32c
Create Date: 2026-07-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008_agent_sessions"
down_revision: str | Sequence[str] | None = "03852067b32c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_sessions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("session_type", sa.String(length=32), nullable=False),
        sa.Column("phase", sa.String(length=32), nullable=False),
        sa.Column("skill_name", sa.String(length=64), nullable=True),
        sa.Column(
            "conversation",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "reasoning_log",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "tool_results",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("current_iteration", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("max_iterations", sa.Integer(), nullable=False, server_default=sa.text("8")),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("output_json", postgresql.JSONB(), nullable=True),
        sa.Column("validation_is_valid", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("validation_errors", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_llm_calls", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("user_instructions", sa.Text(), nullable=True),
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
    op.create_index("ix_agent_sessions_project_id", "agent_sessions", ["project_id"])
    op.create_index(
        "ix_agent_sessions_project_phase",
        "agent_sessions",
        ["project_id", "phase", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_sessions_project_phase", table_name="agent_sessions")
    op.drop_index("ix_agent_sessions_project_id", table_name="agent_sessions")
    op.drop_table("agent_sessions")
