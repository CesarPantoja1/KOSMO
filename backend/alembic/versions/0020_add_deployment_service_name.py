"""persist the Railway service display name

Revision ID: 0020_add_deployment_service_name
Revises: 0019_add_deployment_fields
Create Date: 2026-09-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0020_add_deployment_service_name"
down_revision: str | None = "0019_add_deployment_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("project_integrations", sa.Column("service_name", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("project_integrations", "service_name")
