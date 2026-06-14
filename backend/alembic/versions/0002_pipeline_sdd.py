"""Add pipeline sdd tables

Revision ID: 0002_pipeline_sdd
Revises: 0002_audit_log
Create Date: 2026-06-13

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_pipeline_sdd"
down_revision: Union[str, None] = "0002_audit_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.String(64), nullable=False, index=True),
        sa.Column(
            "current_phase",
            sa.String(32),
            nullable=False,
            server_default="descubrimiento",
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="en_proceso"),
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

    op.create_table(
        "features",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("project_id", sa.String(64), nullable=False, index=True),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="borrador"),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "inferred_from",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("requirements_document", postgresql.JSONB(), nullable=True),
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

    op.create_table(
        "requirements",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("feature_id", sa.String(64), nullable=False, index=True),
        sa.Column("feature_number", sa.Integer(), nullable=False),
        sa.Column("requirement_number", sa.Integer(), nullable=False),
        sa.Column("pattern", sa.String(32), nullable=False),
        sa.Column("trigger", sa.Text(), nullable=False),
        sa.Column("system", sa.String(255), nullable=False),
        sa.Column("response", sa.Text(), nullable=False),
        sa.Column("source_statement", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "traceability",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "acceptance_criteria",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "pipeline_states",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("project_id", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("pipeline_id", sa.String(64), unique=True, nullable=False),
        sa.Column(
            "current_phase",
            sa.String(32),
            nullable=False,
            server_default="descubrimiento",
        ),
        sa.Column(
            "state_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
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


def downgrade() -> None:
    op.drop_table("pipeline_states")
    op.drop_table("requirements")
    op.drop_table("features")
    op.drop_table("projects")
