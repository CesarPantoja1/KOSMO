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
from kosmo.domain.sdd.id_generator import IdGenerator
from kosmo.infrastructure.persistence.postgres.models import ChatHistoryModel, PlanChangeModel


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
        history = await self.get_history(project_id, phase, context_id)
        if history is None:
            history = HistorialChat(
                id=ChatHistoryId(IdGenerator.generate("chat_history")),
                project_id=project_id,
                phase=phase,
                context_id=context_id,
            )
        history = history.add_message(message)
        await self.save_history(history)
        return message

    async def get_history(
        self,
        project_id: ProjectId,
        phase: SpecPhase,
        context_id: str | None = None,
    ) -> HistorialChat | None:
        stmt = select(ChatHistoryModel).where(
            ChatHistoryModel.project_id == str(project_id),
            ChatHistoryModel.phase == phase.value,
        )
        if context_id:
            stmt = stmt.where(ChatHistoryModel.context_id == context_id)
        else:
            stmt = stmt.where(ChatHistoryModel.context_id.is_(None))

        async with self._session_factory() as session:
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                return None

            # Parse messages
            messages: list[MensajeChat] = []
            for msg_dict in model.messages:
                sugg_dict = msg_dict.get("suggested_change")
                sugg = None
                if sugg_dict:
                    diff_dict = sugg_dict.get("diff", {})
                    sugg = SugerenciaCambio(
                        id=sugg_dict["id"],
                        section=sugg_dict["section"],
                        description=sugg_dict["description"],
                        diff=DiffCambio(before=diff_dict.get("before", ""), after=diff_dict.get("after", "")),
                        rationale=sugg_dict.get("rationale"),
                    )
                import datetime

                ts_str = msg_dict["timestamp"]
                ts = (
                    datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if isinstance(ts_str, str)
                    else msg_dict["timestamp"]
                )

                messages.append(
                    MensajeChat(
                        id=ChatMessageId(msg_dict["id"]),
                        role=ChatRole(msg_dict["role"]),
                        content=msg_dict["content"],
                        timestamp=ts,
                        suggested_change=sugg,
                        error=msg_dict.get("error"),
                    )
                )

            return HistorialChat(
                id=ChatHistoryId(model.id),
                project_id=ProjectId(model.project_id),
                phase=SpecPhase(model.phase),
                context_id=model.context_id,
                messages=tuple(messages),
            )

    async def save_history(
        self,
        history: HistorialChat,
    ) -> HistorialChat:
        stmt = select(ChatHistoryModel).where(ChatHistoryModel.id == str(history.id))
        async with self._session_factory() as session:
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            serialized_messages: list[dict[str, Any]] = []
            for m in history.messages:
                msg_dict: dict[str, Any] = {
                    "id": str(m.id),
                    "role": m.role.value,
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat(),
                    "error": m.error,
                }
                if m.suggested_change:
                    msg_dict["suggested_change"] = {
                        "id": m.suggested_change.id,
                        "section": m.suggested_change.section,
                        "description": m.suggested_change.description,
                        "diff": {
                            "before": m.suggested_change.diff.before,
                            "after": m.suggested_change.diff.after,
                        },
                        "rationale": m.suggested_change.rationale,
                    }
                serialized_messages.append(msg_dict)

            if model is None:
                model = ChatHistoryModel(
                    id=str(history.id),
                    project_id=str(history.project_id),
                    phase=history.phase.value,
                    context_id=history.context_id,
                    messages=serialized_messages,
                )
                session.add(model)
            else:
                model.messages = serialized_messages

            await session.commit()
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
            context_id=None,
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
