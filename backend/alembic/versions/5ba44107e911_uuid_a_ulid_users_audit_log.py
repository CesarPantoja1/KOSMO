"""uuid_a_ulid_users_audit_log

Revision ID: 5ba44107e911
Revises: 186053043e79
Create Date: 2026-08-01

"""

from collections.abc import Sequence

from alembic import op

revision: str = "5ba44107e911"
down_revision: str | Sequence[str] | None = "186053043e79"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ALTER COLUMN id TYPE varchar(64) USING id::text")
    op.execute("ALTER TABLE audit_log ALTER COLUMN id TYPE varchar(64) USING id::text")
    op.execute("ALTER TABLE audit_log ALTER COLUMN actor_id TYPE varchar(64) USING actor_id::text")


def downgrade() -> None:
    op.execute("ALTER TABLE users ALTER COLUMN id TYPE uuid USING id::uuid")
    op.execute("ALTER TABLE audit_log ALTER COLUMN id TYPE uuid USING id::uuid")
    op.execute("ALTER TABLE audit_log ALTER COLUMN actor_id TYPE uuid USING actor_id::uuid")
