from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, func, text
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from kosmo.domain.sdd.id_generator import IdGenerator


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: IdGenerator.generate("user")
    )
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

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: IdGenerator.generate("audit")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
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
