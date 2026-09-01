"""add deployment fields to project_integrations table

Revision ID: 0019_add_deployment_fields
Revises: 0018_add_name_avatar_to_users
Create Date: 2026-08-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op

revision: str = "0019_add_deployment_fields"
down_revision: str | None = "0018_add_name_avatar_to_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "project_integrations",
        sa.Column("service_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "project_integrations",
        sa.Column("public_url", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "project_integrations",
        sa.Column(
            "deploy_status",
            sa.String(length=32),
            server_default="not_created",
            nullable=False,
        ),
    )
    op.add_column(
        "project_integrations",
        sa.Column("build_logs_url", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "project_integrations",
        sa.Column("last_deployed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "project_integrations",
        sa.Column(
            "volumes",
            pg.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "project_integrations",
        sa.Column(
            "ports",
            pg.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "project_integrations",
        sa.Column(
            "env_vars",
            pg.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("project_integrations", "env_vars")
    op.drop_column("project_integrations", "ports")
    op.drop_column("project_integrations", "volumes")
    op.drop_column("project_integrations", "last_deployed_at")
    op.drop_column("project_integrations", "build_logs_url")
    op.drop_column("project_integrations", "deploy_status")
    op.drop_column("project_integrations", "public_url")
    op.drop_column("project_integrations", "service_id")
