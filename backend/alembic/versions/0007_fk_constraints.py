"""add foreign key constraints with cascade delete

Revision ID: 0007_fk_constraints
Revises: 0006_requirements
Create Date: 2026-06-30
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007_fk_constraints"
down_revision: str | None = "0006_requirements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_discovery_project",
        "discovery",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_features_discovery",
        "features",
        "discovery",
        ["project_id"],
        ["project_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_requirements_feature",
        "requirements",
        "features",
        ["feature_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_requirements_feature", "requirements", type_="foreignkey")
    op.drop_constraint("fk_features_discovery", "features", type_="foreignkey")
    op.drop_constraint("fk_discovery_project", "discovery", type_="foreignkey")
