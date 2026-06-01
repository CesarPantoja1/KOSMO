from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from kosmo.domain.sdd.id_generator import IdGenerator
from kosmo.infrastructure.persistence.postgres.models import Base


class FeatureModel(Base):
    __tablename__ = "features"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: IdGenerator.generate("feature")
    )
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="borrador")
    requirements_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    requirements_document: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
