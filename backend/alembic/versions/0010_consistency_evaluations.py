"""crear tabla consistency_evaluations

Revision ID: 0010_consistency_evaluations
Revises: 24c223cfecc1
Create Date: 2026-08-14 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op

revision: str = "0010_consistency_evaluations"
down_revision: str | Sequence[str] | None = "24c223cfecc1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "consistency_evaluations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("project_id", sa.String(64), nullable=False, index=True),
        sa.Column("source_phase", sa.String(32), nullable=False),
        sa.Column("target_phase", sa.String(32), nullable=False, index=True),
        sa.Column("target_artifact_id", sa.String(64), nullable=False),
        sa.Column("artifact_type", sa.String(32), nullable=False),
        sa.Column("snapshot_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="evaluating"),
        sa.Column("result", pg.JSONB(), nullable=True),
        sa.Column(
            "source_changes",
            pg.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("failure_reason", sa.Text(), nullable=True),
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
        sa.UniqueConstraint(
            "project_id",
            "source_phase",
            "target_phase",
            "target_artifact_id",
            name="uq_consistency_evaluations_natural",
        ),
    )


def downgrade() -> None:
    op.drop_table("consistency_evaluations")
