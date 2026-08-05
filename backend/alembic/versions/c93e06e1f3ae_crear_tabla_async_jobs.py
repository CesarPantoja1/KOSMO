"""crear_tabla_async_jobs

Revision ID: c93e06e1f3ae
Revises: 5ba44107e911
Create Date: 2026-08-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op

revision: str = "c93e06e1f3ae"
down_revision: str | Sequence[str] | None = "5ba44107e911"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "async_jobs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("job_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("project_id", sa.String(64), nullable=False, index=True),
        sa.Column("result_json", pg.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("async_jobs")
