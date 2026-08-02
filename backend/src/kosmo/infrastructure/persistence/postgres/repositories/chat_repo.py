from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.chat import (
    ChatRepository,
    ChatRole,
    DiffCambio,
    EstadoPlanCambio,
    HistorialChat,
    MensajeChat,
    PlanCambio,
    SugerenciaCambio,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import ChatHistoryId, ChatMessageId, PlanChangeId, ProjectId
from kosmo.infrastructure.persistence.postgres.models import ChatMessageModel, PlanChangeModel


class SqlAlchemyChatRepository(ChatRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save_message(
        self,
        project_id: ProjectId,
        phase: SpecPhase,
        message: MensajeChat,
        context_id: str | None = None,
    ) -> MensajeChat:
        suggested_change: dict[str, Any] | None = None
        if message.suggested_change:
            sc = message.suggested_change
            suggested_change = {
                "id": sc.id,
                "section": sc.section,
                "description": sc.description,
                "diff": {"before": sc.diff.before, "after": sc.diff.after},
                "rationale": sc.rationale,
            }

        model = ChatMessageModel(
            id=str(message.id),
            project_id=str(project_id),
            phase=phase.value,
            context_id=context_id,
            role=message.role.value,
            content=message.content,
            suggested_change=suggested_change,
            error=message.error,
        )
        async with self._session_factory() as session:
            session.add(model)
            await session.commit()
        return message

    async def get_history(
        self,
        project_id: ProjectId,
        phase: SpecPhase,
        context_id: str | None = None,
        limit: int = 200,
        before: str | None = None,
    ) -> HistorialChat | None:
        stmt = select(ChatMessageModel).where(
            ChatMessageModel.project_id == str(project_id),
            ChatMessageModel.phase == phase.value,
        )
        if context_id:
            stmt = stmt.where(ChatMessageModel.context_id == context_id)
        else:
            stmt = stmt.where(ChatMessageModel.context_id.is_(None))

        if before:
            from datetime import datetime as _datetime

            cursor_dt = _datetime.fromisoformat(before)
            stmt = stmt.where(ChatMessageModel.created_at < cursor_dt)

        stmt = stmt.order_by(ChatMessageModel.created_at.desc()).limit(limit)

        async with self._session_factory() as session:
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
            messages=messages,
            has_more=has_more,
            next_cursor=next_cursor,
        )

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
        async with self._session_factory() as session:
            session.add(model)
            await session.commit()
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

        async with self._session_factory() as session:
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
        *,
        _session: AsyncSession | None = None,
    ) -> PlanCambio | None:
        stmt = select(PlanChangeModel).where(
            PlanChangeModel.project_id == str(project_id), PlanChangeModel.id == str(change_id)
        )

        if _session is not None:
            result = await _session.execute(stmt)
            model = result.scalar_one_or_none()
            if not model:
                return None
            model.status = status.value
            if user_version is not None:
                model.user_version = user_version
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

        async with self._session_factory() as session:
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if not model:
                return None

            model.status = status.value
            if user_version is not None:
                model.user_version = user_version

            await session.commit()
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
        async with self._session_factory() as session:
            result = await session.execute(stmt)
            await session.commit()
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
        async with self._session_factory() as session:
            await session.execute(stmt)
            await session.commit()


def _model_to_message(model: ChatMessageModel) -> MensajeChat:
    sugg = None
    if model.suggested_change:
        diff_dict = model.suggested_change.get("diff", {})
        sugg = SugerenciaCambio(
            id=model.suggested_change["id"],
            section=model.suggested_change.get("section", ""),
            description=model.suggested_change.get("description", ""),
            diff=DiffCambio(
                before=diff_dict.get("before", ""),
                after=diff_dict.get("after", ""),
            ),
            rationale=model.suggested_change.get("rationale"),
        )

    return MensajeChat(
        id=ChatMessageId(model.id),
        role=ChatRole(model.role),
        content=model.content,
        timestamp=model.created_at if model.created_at else datetime.now(UTC),
        suggested_change=sugg,
        error=model.error,
    )
