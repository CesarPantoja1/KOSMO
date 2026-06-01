from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from kosmo.domain.sdd.id_generator import IdGenerator
from kosmo.infrastructure.persistence.postgres.models import Base


class SpecModel(Base):
    __tablename__ = "specs"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: IdGenerator.generate("spec")
    )
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id"), nullable=False, index=True
    )
    phase: Mapped[str] = mapped_column(String(32), default="descubrimiento")
    discovery_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    roadmap_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    design_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    constitution_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class RequirementModel(Base):
    __tablename__ = "requirements"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    spec_id: Mapped[str] = mapped_column(String(32), ForeignKey("specs.id"), index=True)
    pattern: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger: Mapped[str | None] = mapped_column(Text, nullable=True)
    system: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    acceptance_criteria: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    source_statement: Mapped[str] = mapped_column(Text, nullable=False)
    traceability: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)


class TaskModel(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    spec_id: Mapped[str] = mapped_column(String(32), ForeignKey("specs.id"), index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    boundary: Mapped[str] = mapped_column(String(128), nullable=False)
    depends_on: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    requirements: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    acceptance_criteria: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    parallelizable: Mapped[bool] = mapped_column(Boolean, default=False)
    implementation_notes: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)


class ConstitutionModel(Base):
    __tablename__ = "constitutions"

    project_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    product: Mapped[str] = mapped_column(Text, default="")
    tech: Mapped[str] = mapped_column(Text, default="")
    structure: Mapped[str] = mapped_column(Text, default="")
    custom_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    version_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class PipelineEventModel(Base):
    __tablename__ = "pipeline_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(32), unique=True)
    spec_id: Mapped[str] = mapped_column(String(32), index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class EncryptedApiKeyModel(Base):
    __tablename__ = "encrypted_api_keys"

    key_id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: IdGenerator.generate("apikey")
    )
    user_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    cipher_text: Mapped[str] = mapped_column(Text, nullable=False)
    model_default: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class ArtifactModel(Base):
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    spec_id: Mapped[str] = mapped_column(String(32), index=True)
    kind: Mapped[str] = mapped_column(String(64))
    blob_key: Mapped[str] = mapped_column(String(256))
    content_sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
