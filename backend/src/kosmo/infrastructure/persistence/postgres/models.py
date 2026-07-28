from datetime import datetime
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import Vector  # pyright: ignore[reportMissingTypeStubs]
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
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    disabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class AuditEventModel(Base):
    __tablename__ = "audit_log"

    id: Mapped[UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
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
        "metadata",
        pg.JSONB(),
        nullable=False,
        server_default=text("'{}'::jsonb"),
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class FeatureModel(Base):
    __tablename__ = "features"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text(), nullable=False)
    origin: Mapped[str] = mapped_column(Text(), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RequirementModel(Base):
    __tablename__ = "requirements"

    feature_id: Mapped[str] = mapped_column(String(64), primary_key=True, nullable=False)
    markdown: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DiscoveryDocumentModel(Base):
    __tablename__ = "discovery"

    project_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        nullable=False,
    )
    markdown: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AgentSessionModel(Base):
    __tablename__ = "agent_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_type: Mapped[str] = mapped_column(String(32), nullable=False)
    phase: Mapped[str] = mapped_column(String(32), nullable=False)
    skill_name: Mapped[str | None] = mapped_column(String(64), nullable=True)

    conversation: Mapped[list[Any]] = mapped_column(pg.JSONB(), nullable=False, server_default=text("'[]'::jsonb"))
    reasoning_log: Mapped[list[Any]] = mapped_column(pg.JSONB(), nullable=False, server_default=text("'[]'::jsonb"))
    tool_results: Mapped[list[Any]] = mapped_column(pg.JSONB(), nullable=False, server_default=text("'[]'::jsonb"))

    current_iteration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_iterations: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    is_completed: Mapped[bool] = mapped_column(default=False, nullable=False)

    output_json: Mapped[str | None] = mapped_column(pg.JSONB(), nullable=True)
    validation_is_valid: Mapped[bool] = mapped_column(default=False, nullable=False)
    validation_errors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validation_error_messages: Mapped[list[Any]] = mapped_column(
        pg.JSONB(), nullable=False, server_default=text("'[]'::jsonb")
    )
    total_llm_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    user_instructions: Mapped[str | None] = mapped_column(Text(), nullable=True)

    embedding: Mapped[list[float] | None] = mapped_column(Vector, nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(64), nullable=True)

    reflection: Mapped[str | None] = mapped_column(Text(), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ActivityDiagramModel(Base):
    __tablename__ = "activity_diagrams"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    feature_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    diagram_syntax: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class KnowledgePatternModel(Base):
    __tablename__ = "knowledge_patterns"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    phase: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    pattern_text: Mapped[str] = mapped_column(Text(), nullable=False)
    support_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ChatHistoryModel(Base):
    __tablename__ = "chat_histories"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    phase: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    context_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    messages: Mapped[list[Any]] = mapped_column(pg.JSONB(), nullable=False, server_default=text("'[]'::jsonb"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PlanChangeModel(Base):
    __tablename__ = "plan_changes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    phase: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    context_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    section: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text(), nullable=False)
    diff_before: Mapped[str] = mapped_column(Text(), nullable=False)
    diff_after: Mapped[str] = mapped_column(Text(), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text(), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    origin: Mapped[str] = mapped_column(String(64), nullable=False)
    user_version: Mapped[str | None] = mapped_column(Text(), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
