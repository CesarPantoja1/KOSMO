"""fix_features_fk_projects

Revision ID: 99ffc4fbdb91
Revises: b3a40a8da1d6
Create Date: 2026-08-04 13:17:03.644994

"""

from collections.abc import Sequence

from alembic import op

revision: str = "99ffc4fbdb91"
down_revision: str | Sequence[str] | None = "b3a40a8da1d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("fk_features_discovery", "features", type_="foreignkey")
    op.create_foreign_key(
        "fk_features_project",
        "features",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_features_project", "features", type_="foreignkey")
    op.create_foreign_key(
        "fk_features_discovery",
        "features",
        "discovery",
        ["project_id"],
        ["project_id"],
        ondelete="CASCADE",
    )
