from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Integer, String, Text, func, text
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(pg.CITEXT(), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEventModel(Base):
    __tablename__ = "audit_log"

    id: Mapped[UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[UUID | None] = mapped_column(pg.UUID(as_uuid=True), nullable=True)
    actor_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(pg.INET(), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text(), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata", pg.JSONB(), nullable=False, server_default=text("'{}'::jsonb")
    )


class ProjectModel(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text(), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    current_phase: Mapped[str] = mapped_column(String(32), nullable=False, default="descubrimiento")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="en_proceso")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class FeatureModel(Base):
    __tablename__ = "features"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text(), nullable=False)
    rationale: Mapped[str] = mapped_column(Text(), nullable=False, default="")
    inferred_from: Mapped[dict[str, Any]] = mapped_column(
        pg.JSONB(), nullable=False, server_default=text("'[]'::jsonb")
    )
    requirements_document: Mapped[dict[str, Any] | None] = mapped_column(pg.JSONB(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RequirementModel(Base):
    __tablename__ = "requirements"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    feature_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    feature_number: Mapped[int] = mapped_column(Integer, nullable=False)
    requirement_number: Mapped[int] = mapped_column(Integer, nullable=False)
    pattern: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger: Mapped[str] = mapped_column(Text(), nullable=False)
    system: Mapped[str] = mapped_column(String(255), nullable=False)
    response: Mapped[str] = mapped_column(Text(), nullable=False)
    source_statement: Mapped[str] = mapped_column(Text(), nullable=False)
    rationale: Mapped[str] = mapped_column(Text(), nullable=False, default="")
    traceability: Mapped[dict[str, Any]] = mapped_column(
        pg.JSONB(), nullable=False, server_default=text("'[]'::jsonb")
    )
    acceptance_criteria: Mapped[dict[str, Any]] = mapped_column(
        pg.JSONB(), nullable=False, server_default=text("'[]'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DiscoveryDocumentModel(Base):
    __tablename__ = "discovery"

    project_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        nullable=False,
    )
    markdown: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PipelineStateModel(Base):
    __tablename__ = "pipeline_states"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    pipeline_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    current_phase: Mapped[str] = mapped_column(String(32), nullable=False, default="descubrimiento")
    state_json: Mapped[dict[str, Any]] = mapped_column(
        pg.JSONB(), nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
