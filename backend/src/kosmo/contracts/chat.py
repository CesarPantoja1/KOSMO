from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from kosmo.contracts.sdd.ids import ChatMessageId


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass(frozen=True)
class DiffCambio:
    before: str
    after: str


@dataclass(frozen=True)
class SugerenciaCambio:
    id: str
    section: str
    description: str
    diff: DiffCambio


@dataclass(frozen=True)
class MensajeChat:
    id: ChatMessageId
    role: ChatRole
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    suggested_change: SugerenciaCambio | None = None
