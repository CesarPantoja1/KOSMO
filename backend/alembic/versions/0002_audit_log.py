"""create audit_log table

Revision ID: 0002_audit_log
Revises: 0001_users
Create Date: 2026-05-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID

from alembic import op

revision: str = "0002_audit_log"
down_revision: str | None = "0001_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("actor_id", UUID(as_uuid=True), nullable=True),
        sa.Column("actor_email", sa.String(length=320), nullable=True),
        sa.Column("ip_address", INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("resource_type", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.String(length=128), nullable=True),
        sa.Column(
            "metadata",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.CheckConstraint(
            "outcome IN ('success', 'failure')",
            name="ck_audit_log_outcome",
        ),
    )
    op.create_index(
        "ix_audit_log_created_at",
        "audit_log",
        [sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_audit_log_event_type_created_at",
        "audit_log",
        ["event_type", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_audit_log_actor_id_created_at",
        "audit_log",
        ["actor_id", sa.text("created_at DESC")],
    )
    op.create_index("ix_audit_log_request_id", "audit_log", ["request_id"])
    op.create_index(
        "ix_audit_log_failures",
        "audit_log",
        ["event_type", sa.text("created_at DESC")],
        postgresql_where=sa.text("outcome = 'failure'"),
    )


def downgrade() -> None:
    op.drop_index("ix_audit_log_failures", table_name="audit_log")
    op.drop_index("ix_audit_log_request_id", table_name="audit_log")
    op.drop_index("ix_audit_log_actor_id_created_at", table_name="audit_log")
    op.drop_index("ix_audit_log_event_type_created_at", table_name="audit_log")
    op.drop_index("ix_audit_log_created_at", table_name="audit_log")
    op.drop_table("audit_log")
