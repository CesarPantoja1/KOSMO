"""agregar unique constraints y fks cascade

Revision ID: 276a31b1b4c2
Revises: 4d1f8392bd76
Create Date: 2026-07-31

"""

from collections.abc import Sequence

from alembic import op

revision: str = "276a31b1b4c2"
down_revision: str | Sequence[str] | None = "4d1f8392bd76"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint("uq_features_project_number", "features", ["project_id", "number"])
    op.create_unique_constraint("uq_knowledge_patterns_phase_pattern", "knowledge_patterns", ["phase", "pattern_text"])

    op.create_foreign_key(
        "fk_chat_messages_project",
        "chat_messages",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_plan_changes_project",
        "plan_changes",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_agent_sessions_project",
        "agent_sessions",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_agent_sessions_project", "agent_sessions", type_="foreignkey")
    op.drop_constraint("fk_plan_changes_project", "plan_changes", type_="foreignkey")
    op.drop_constraint("fk_chat_messages_project", "chat_messages", type_="foreignkey")
    op.drop_constraint("uq_knowledge_patterns_phase_pattern", "knowledge_patterns", type_="unique")
    op.drop_constraint("uq_features_project_number", "features", type_="unique")
