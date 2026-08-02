from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel

from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import ChatHistoryId, ChatMessageId, PlanChangeId, ProjectId


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class EstadoPlanCambio(StrEnum):
    PENDING = "pending"
    ADDED = "added"
    CONFLICT = "conflict"
    APPLIED = "applied"
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
    rationale: str | None = None


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
    context_id: str | None = None


@dataclass(frozen=True)
class MensajeChat:
    id: ChatMessageId
    role: ChatRole
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    suggested_changes: list[SugerenciaCambio] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    error: str | None = None


@dataclass(frozen=True)
class HistorialChat:
    id: ChatHistoryId
    project_id: ProjectId
    phase: SpecPhase
    context_id: str | None = None
    messages: tuple[MensajeChat, ...] = field(default_factory=tuple)
    has_more: bool = False
    next_cursor: str | None = None

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

    @property
    def composite_key(self) -> str:
        return f"{self.project_id}:{self.phase.value}:{self.context_id or ''}"


class ChatRepository(Protocol):
    async def save_message(
        self,
        project_id: ProjectId,
        phase: SpecPhase,
        message: MensajeChat,
        context_id: str | None = None,
    ) -> MensajeChat: ...

    async def get_history(
        self,
        project_id: ProjectId,
        phase: SpecPhase,
        context_id: str | None = None,
        limit: int = 200,
        before: str | None = None,
    ) -> HistorialChat | None: ...

    async def save_history(
        self,
        history: HistorialChat,
    ) -> HistorialChat: ...

    async def add_plan_change(
        self,
        project_id: ProjectId,
        phase: SpecPhase,
        change: PlanCambio,
    ) -> PlanCambio: ...

    async def list_plan_changes(
        self,
        project_id: ProjectId,
        phase: SpecPhase | None = None,
    ) -> list[PlanCambio]: ...

    async def update_plan_change_status(
        self,
        project_id: ProjectId,
        change_id: PlanChangeId,
        status: EstadoPlanCambio,
        user_version: str | None = None,
    ) -> PlanCambio | None: ...

    async def remove_plan_change(
        self,
        project_id: ProjectId,
        change_id: PlanChangeId,
    ) -> bool: ...

    async def clear_plan(
        self,
        project_id: ProjectId,
        phase: SpecPhase | None = None,
    ) -> None: ...


class SugerenciaCambioLLM(BaseModel):
    section: str
    description: str
    diff_before: str
    diff_after: str
    rationale: str | None = None


class RespuestaChatLLM(BaseModel):
    content: str
    change_suggestions: list[SugerenciaCambioLLM] | None = None
