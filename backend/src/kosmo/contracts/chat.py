from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import ChatHistoryId, ChatMessageId, PlanChangeId, ProjectId


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class EstadoPlanCambio(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    CONFLICT = "conflict"
    DISCARDED = "discarded"


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
class PlanCambio:
    id: PlanChangeId
    section: str
    description: str
    diff: DiffCambio
    status: EstadoPlanCambio = EstadoPlanCambio.PENDING
    origin: str = "Chat Descubrimiento"
    rationale: str | None = None
    user_version: str | None = None


@dataclass(frozen=True)
class MensajeChat:
    id: ChatMessageId
    role: ChatRole
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    suggested_change: SugerenciaCambio | None = None


@dataclass(frozen=True)
class HistorialChat:
    id: ChatHistoryId
    project_id: ProjectId
    phase: SpecPhase
    context_id: str | None = None
    messages: tuple[MensajeChat, ...] = field(default_factory=tuple)

    def add_message(self, message: MensajeChat) -> HistorialChat:
        return HistorialChat(
            id=self.id,
            project_id=self.project_id,
            phase=self.phase,
            context_id=self.context_id,
            messages=(*self.messages, message),
        )

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def last_message(self) -> MensajeChat | None:
        return self.messages[-1] if self.messages else None


