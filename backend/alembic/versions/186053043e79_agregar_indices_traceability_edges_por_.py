"""agregar_indices_traceability_edges_por_id

Revision ID: 186053043e79
Revises: 495f1e2ae4c7
Create Date: 2026-08-01

"""

from collections.abc import Sequence

from alembic import op

revision: str = "186053043e79"
down_revision: str | Sequence[str] | None = "495f1e2ae4c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_traceability_edges_source_id", "traceability_edges", ["source_id"], if_not_exists=True
    )
    op.create_index(
        "ix_traceability_edges_target_id", "traceability_edges", ["target_id"], if_not_exists=True
    )


def downgrade() -> None:
    op.drop_index("ix_traceability_edges_source_id", table_name="traceability_edges", if_exists=True)
    op.drop_index("ix_traceability_edges_target_id", table_name="traceability_edges", if_exists=True)
