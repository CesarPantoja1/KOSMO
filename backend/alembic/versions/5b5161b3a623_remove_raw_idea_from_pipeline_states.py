"""remove_raw_idea_from_pipeline_states

Revision ID: 5b5161b3a623
Revises: 9313ffd42cf9
Create Date: 2026-06-13 20:23:42.081300

"""

from collections.abc import Sequence

from alembic import op

revision: str = "5b5161b3a623"
down_revision: str | None = "9313ffd42cf9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE pipeline_states SET state_json = state_json - 'raw_idea'"
    )


def downgrade() -> None:
    pass
