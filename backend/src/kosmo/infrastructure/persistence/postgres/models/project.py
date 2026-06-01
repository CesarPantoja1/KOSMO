from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from kosmo.domain.sdd.id_generator import IdGenerator
from kosmo.infrastructure.persistence.postgres.models import Base


class ProjectModel(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: IdGenerator.generate("project")
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    current_phase: Mapped[str] = mapped_column(String(32), default="descubrimiento")
    status: Mapped[str] = mapped_column(String(32), default="en_progreso")
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    discovery_document: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
