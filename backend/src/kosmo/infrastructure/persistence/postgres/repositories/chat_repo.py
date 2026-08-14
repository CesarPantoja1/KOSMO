from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.chat import (
    ChatRepository,
    ChatRole,
    ChatSession,
    ChatSessionSummary,
    DiffCambio,
    EstadoPlanCambio,
    HistorialChat,
    MensajeChat,
    PlanCambio,
    SugerenciaCambio,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import (
    ChatHistoryId,
    ChatMessageId,
    ChatSessionId,
    PlanChangeId,
    ProjectId,
)
from kosmo.infrastructure.persistence.postgres.models import (
    ChatMessageModel,
    ChatSessionModel,
    PlanChangeModel,
)


class SqlAlchemyChatRepository(ChatRepository):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        if session_factory is None and session is None:
            raise ValueError("Se requiere session_factory o session")
        self._session_factory = session_factory
        self._session = session

    @asynccontextmanager
    async def _session_ctx(self) -> AsyncGenerator[AsyncSession]:
        if self._session is not None:
            yield self._session
            return
        assert self._session_factory is not None
        async with self._session_factory() as session:
            yield session

    async def _commit(self, session: AsyncSession) -> None:
        if self._session is None:
            await session.commit()

    async def save_message(
        self,
        project_id: ProjectId,
        phase: SpecPhase,
        message: MensajeChat,
        context_id: str | None = None,
        session_id: ChatSessionId | None = None,
    ) -> MensajeChat:
        suggested_changes: list[dict[str, Any]] | None = None
        if message.suggested_changes:
            suggested_changes = [
                {
                    "id": sc.id,
                    "section": sc.section,
                    "description": sc.description,
                    "diff": {"before": sc.diff.before, "after": sc.diff.after},
                    "rationale": sc.rationale,
                    "applied": sc.applied,
                    "not_applied_reason": sc.not_applied_reason,
                }
                for sc in message.suggested_changes
            ]

        model = ChatMessageModel(
            id=str(message.id),
            project_id=str(project_id),
            phase=phase.value,
            context_id=context_id,
            session_id=str(session_id) if session_id is not None else None,
            role=message.role.value,
            content=message.content,
            suggested_change=suggested_changes,
            error=message.error,
        )
        async with self._session_ctx() as session:
            session.add(model)
            await self._commit(session)
        return message

    async def get_history(
        self,
        project_id: ProjectId,
        phase: SpecPhase,
        context_id: str | None = None,
        limit: int = 200,
        before: str | None = None,
        session_id: ChatSessionId | None = None,
    ) -> HistorialChat | None:
        stmt = select(ChatMessageModel).where(
            ChatMessageModel.project_id == str(project_id),
            ChatMessageModel.phase == phase.value,
        )
        if session_id is not None:
            stmt = stmt.where(ChatMessageModel.session_id == str(session_id))
        elif context_id:
            stmt = stmt.where(ChatMessageModel.context_id == context_id)
        else:
            stmt = stmt.where(ChatMessageModel.context_id.is_(None))

        if before:
            from datetime import datetime as _datetime

            cursor_dt = _datetime.fromisoformat(before)
            stmt = stmt.where(ChatMessageModel.created_at < cursor_dt)

        stmt = stmt.order_by(ChatMessageModel.created_at.desc()).limit(limit)

        async with self._session_ctx() as session:
            result = await session.execute(stmt)
            models = list(result.scalars().all())

        if not models:
            return None

        models.reverse()
        messages = tuple(_model_to_message(m) for m in models)

        history_id = self._compose_history_id(project_id, phase, context_id)

        has_more = len(models) == limit
        next_cursor = models[0].created_at.isoformat() if has_more else None

        return HistorialChat(
            id=ChatHistoryId(history_id),
            project_id=project_id,
            phase=phase,
            context_id=context_id,
            session_id=session_id,
            messages=messages,
            has_more=has_more,
            next_cursor=next_cursor,
        )

    async def create_session(self, session: ChatSession) -> ChatSession:
        model = ChatSessionModel(
            id=str(session.id),
            project_id=str(session.project_id),
            phase=session.phase.value,
            context_id=session.context_id,
        )
        async with self._session_ctx() as db:
            db.add(model)
            await self._commit(db)
        return session

    async def list_sessions(
        self,
        project_id: ProjectId,
        phase: SpecPhase,
        *,
        context_id: str | None = None,
    ) -> list[ChatSessionSummary]:
        stmt = (
            select(
                ChatSessionModel,
                func.count(ChatMessageModel.id),
                func.max(ChatMessageModel.created_at),
            )
            .outerjoin(ChatMessageModel, ChatMessageModel.session_id == ChatSessionModel.id)
            .where(
                ChatSessionModel.project_id == str(project_id),
                ChatSessionModel.phase == phase.value,
            )
            .group_by(ChatSessionModel.id)
            .order_by(ChatSessionModel.created_at.desc())
        )
        if context_id is not None:
            stmt = stmt.where(ChatSessionModel.context_id == context_id)

        async with self._session_ctx() as db:
            result = await db.execute(stmt)
            rows = result.all()

        return [
            ChatSessionSummary(
                id=ChatSessionId(model.id),
                phase=SpecPhase(model.phase),
                context_id=model.context_id,
                created_at=model.created_at,
                message_count=int(count or 0),
                last_message_at=last_at,
            )
            for model, count, last_at in rows
        ]

    @staticmethod
    def _compose_history_id(project_id: ProjectId, phase: SpecPhase, context_id: str | None) -> str:
        return f"{project_id}:{phase.value}:{context_id or ''}"

    # ponytail: no-op — el historial se persiste como mensajes individuales (save_message).
    # save_history existe por el contrato ChatRepository Protocol; eliminar cuando el
    # contrato migre a append-only.
    async def save_history(
        self,
        history: HistorialChat,
    ) -> HistorialChat:
        return history

    async def add_plan_change(
        self,
        project_id: ProjectId,
        phase: SpecPhase,
        change: PlanCambio,
    ) -> PlanCambio:
        model = PlanChangeModel(
            id=str(change.id),
            project_id=str(project_id),
            phase=phase.value,
            context_id=change.context_id,
            section=change.section,
            description=change.description,
            diff_before=change.diff.before,
            diff_after=change.diff.after,
            rationale=change.rationale,
            status=change.status.value,
            origin=change.origin,
            user_version=change.user_version,
        )
        async with self._session_ctx() as session:
            session.add(model)
            await self._commit(session)
            return change

    async def list_plan_changes(
        self,
        project_id: ProjectId,
        phase: SpecPhase | None = None,
    ) -> list[PlanCambio]:
        stmt = select(PlanChangeModel).where(PlanChangeModel.project_id == str(project_id))
        if phase:
            stmt = stmt.where(PlanChangeModel.phase == phase.value)
        stmt = stmt.order_by(PlanChangeModel.created_at, PlanChangeModel.id)

        async with self._session_ctx() as session:
            result = await session.execute(stmt)
            models = result.scalars().all()

            return [
                PlanCambio(
                    id=PlanChangeId(m.id),
                    section=m.section,
                    description=m.description,
                    diff=DiffCambio(before=m.diff_before, after=m.diff_after),
                    status=EstadoPlanCambio(m.status),
                    origin=m.origin,
                    rationale=m.rationale,
                    user_version=m.user_version,
                    context_id=m.context_id,
                )
                for m in models
            ]

    async def update_plan_change_status(
        self,
        project_id: ProjectId,
        change_id: PlanChangeId,
        status: EstadoPlanCambio,
        user_version: str | None = None,
    ) -> PlanCambio | None:
        stmt = select(PlanChangeModel).where(
            PlanChangeModel.project_id == str(project_id), PlanChangeModel.id == str(change_id)
        )

        async with self._session_ctx() as session:
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if not model:
                return None

            model.status = status.value
            if user_version is not None:
                model.user_version = user_version

            await self._commit(session)
            return PlanCambio(
                id=PlanChangeId(model.id),
                section=model.section,
                description=model.description,
                diff=DiffCambio(before=model.diff_before, after=model.diff_after),
                status=EstadoPlanCambio(model.status),
                origin=model.origin,
                rationale=model.rationale,
                user_version=model.user_version,
                context_id=model.context_id,
            )

    async def remove_plan_change(
        self,
        project_id: ProjectId,
        change_id: PlanChangeId,
    ) -> bool:
        stmt = delete(PlanChangeModel).where(
            PlanChangeModel.project_id == str(project_id), PlanChangeModel.id == str(change_id)
        )
        async with self._session_ctx() as session:
            result = await session.execute(stmt)
            await self._commit(session)
            rc = getattr(result, "rowcount", 0)
            return bool(rc > 0)

    async def clear_plan(
        self,
        project_id: ProjectId,
        phase: SpecPhase | None = None,
    ) -> None:
        stmt = delete(PlanChangeModel).where(PlanChangeModel.project_id == str(project_id))
        if phase:
            stmt = stmt.where(PlanChangeModel.phase == phase.value)
        async with self._session_ctx() as session:
            await session.execute(stmt)
            await self._commit(session)


def _model_to_message(model: ChatMessageModel) -> MensajeChat:
    from typing import Any as TypingAny

    suggested_changes: list[SugerenciaCambio] = []
    raw: TypingAny = model.suggested_change
    if raw is not None:
        items: list[TypingAny] = raw if isinstance(raw, list) else [raw]  # type: ignore[reportUnknownVariableType]
        for item in items:
            diff_dict: dict[str, str] = item.get("diff", {})
            suggested_changes.append(
                SugerenciaCambio(
                    id=item["id"],
                    section=item.get("section", ""),
                    description=item.get("description", ""),
                    diff=DiffCambio(
                        before=diff_dict.get("before", ""),
                        after=diff_dict.get("after", ""),
                    ),
                    rationale=item.get("rationale"),
                )
            )

    return MensajeChat(
        id=ChatMessageId(model.id),
        role=ChatRole(model.role),
        content=model.content,
        timestamp=model.created_at if model.created_at else datetime.now(UTC),
        suggested_changes=suggested_changes,
        error=model.error,
    )
