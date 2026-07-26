from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.agent_memory import (
    AgentMemoryPort,
    AgentSession,
    AgentSessionSummary,
    ProjectMemoryContext,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import AgentMemoryId, ProjectId
from kosmo.infrastructure.persistence.postgres.models import AgentSessionModel


class SqlAlchemyAgentSessionStore(AgentMemoryPort):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save_session(self, session: AgentSession) -> None:
        async with self._session_factory() as db:
            stmt = select(AgentSessionModel).where(AgentSessionModel.id == session.session_id)
            result = await db.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                model = AgentSessionModel(id=session.session_id)
                db.add(model)

            model.project_id = session.project_id
            model.session_type = session.session_type
            model.phase = session.phase.value
            model.skill_name = session.skill_name
            model.conversation = list(session.conversation)
            model.reasoning_log = list(session.reasoning_log)
            model.tool_results = list(session.tool_results)
            model.current_iteration = session.current_iteration
            model.max_iterations = session.max_iterations
            model.is_completed = session.is_completed
            model.output_json = _safe_json_dump(session.output_json)
            model.validation_is_valid = session.validation_is_valid
            model.validation_errors = session.validation_errors
            model.validation_error_messages = list(session.validation_error_messages)
            model.total_llm_calls = session.total_llm_calls
            model.user_instructions = session.user_instructions
            model.embedding = list(session.embedding) if session.embedding else None
            model.embedding_model = session.embedding_model
            model.reflection = session.reflection
            model.updated_at = datetime.now(UTC)

            await db.commit()

    async def load_session(self, session_id: AgentMemoryId) -> AgentSession | None:
        async with self._session_factory() as db:
            stmt = select(AgentSessionModel).where(AgentSessionModel.id == session_id)
            result = await db.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return _model_to_session(model)

    async def list_sessions(
        self,
        project_id: ProjectId,
        *,
        phase: SpecPhase | None = None,
    ) -> list[AgentSessionSummary]:
        async with self._session_factory() as db:
            stmt = select(AgentSessionModel).where(AgentSessionModel.project_id == str(project_id))
            if phase is not None:
                stmt = stmt.where(AgentSessionModel.phase == phase.value)
            stmt = stmt.order_by(AgentSessionModel.created_at.desc())
            result = await db.execute(stmt)
            models = result.scalars().all()
            return [_model_to_summary(m) for m in models]

    async def get_latest_session(
        self,
        project_id: ProjectId,
        phase: SpecPhase,
    ) -> AgentSession | None:
        async with self._session_factory() as db:
            stmt = (
                select(AgentSessionModel)
                .where(AgentSessionModel.project_id == str(project_id))
                .where(AgentSessionModel.phase == phase.value)
                .order_by(AgentSessionModel.created_at.desc())
                .limit(1)
            )
            result = await db.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return _model_to_session(model)

    async def get_project_context(self, project_id: ProjectId) -> ProjectMemoryContext:
        summaries = await self.list_sessions(project_id)
        latest: dict[str, AgentSessionSummary] = {}
        for s in summaries:
            key = f"{s.session_type}:{s.phase.value}"
            if key not in latest or s.created_at > latest[key].created_at:
                latest[key] = s

        reflections: list[str] = []
        error_counter: dict[str, int] = {}
        async with self._session_factory() as db:
            stmt = (
                select(AgentSessionModel.reflection)
                .where(AgentSessionModel.project_id == str(project_id))
                .where(AgentSessionModel.reflection.isnot(None))
                .order_by(AgentSessionModel.created_at.desc())
                .limit(5)
            )
            result = await db.execute(stmt)
            for row in result.fetchall():
                if row[0]:
                    reflections.append(str(row[0]))

            errors_stmt = (
                select(AgentSessionModel.validation_error_messages)
                .where(AgentSessionModel.project_id == str(project_id))
                .where(AgentSessionModel.is_completed == False)  # noqa: E712
                .where(AgentSessionModel.validation_error_messages.isnot(None))
                .order_by(AgentSessionModel.created_at.desc())
                .limit(20)
            )
            errors_result = await db.execute(errors_stmt)
            for (msgs,) in errors_result.fetchall():
                for msg in (msgs or []):  # type: ignore[reportUnknownVariableType]
                    error_counter[str(msg)] = error_counter.get(str(msg), 0) + 1  # type: ignore[reportUnknownArgumentType]

        common_errors = [f"{msg} (x{count})" for msg, count in
            sorted(error_counter.items(), key=lambda x: -x[1])[:5]]

        return ProjectMemoryContext(
            project_id=project_id,
            latest_sessions=latest,
            total_sessions=len(summaries),
            common_validation_errors=common_errors,
            recent_reflections=reflections,
        )

    async def get_similar_sessions(
        self,
        embedding: list[float],
        *,
        limit: int = 5,
        exclude_project_id: ProjectId | None = None,
        model: str | None = None,
    ) -> list[AgentSessionSummary]:
        async with self._session_factory() as db:
            embedding_str = f"[{','.join(str(x) for x in embedding)}]"
            filters = "WHERE embedding IS NOT NULL"
            if exclude_project_id:
                filters += " AND project_id != :exclude_id"
            if model:
                filters += " AND embedding_model = :model"
            stmt = text(
                f"SELECT id FROM agent_sessions "
                f"{filters} "
                "ORDER BY embedding <-> :embedding::vector "
                "LIMIT :limit"
            )
            params: dict[str, object] = {
                "embedding": embedding_str,
                "limit": limit,
            }
            if exclude_project_id is not None:
                params["exclude_id"] = str(exclude_project_id)
            if model:
                params["model"] = model

            result = await db.execute(stmt, params)
            rows = result.fetchall()
            summaries: list[AgentSessionSummary] = []
            for row in rows:
                session = await self.load_session(AgentMemoryId(str(row[0])))
                if session is not None:
                    summaries.append(_to_summary(session))
            return summaries


def _to_summary(session: AgentSession) -> AgentSessionSummary:
    return AgentSessionSummary(
        session_id=session.session_id,
        project_id=session.project_id,
        session_type=session.session_type,
        phase=session.phase,
        skill_name=session.skill_name,
        is_completed=session.is_completed,
        total_llm_calls=session.total_llm_calls,
        validation_errors=session.validation_errors,
        user_instructions=session.user_instructions,
        created_at=session.created_at,
    )


def _model_to_session(model: AgentSessionModel) -> AgentSession:
    return AgentSession(
        session_id=AgentMemoryId(model.id),
        project_id=ProjectId(model.project_id),
        session_type=model.session_type,
        phase=SpecPhase(model.phase),
        skill_name=model.skill_name,
        conversation=[str(c) for c in (model.conversation or [])],
        reasoning_log=[str(r) for r in (model.reasoning_log or [])],
        tool_results=[
            dict(t) if isinstance(t, dict) else {}  # type: ignore[reportUnknownArgumentType]
            for t in (model.tool_results or [])
        ],
        current_iteration=model.current_iteration,
        max_iterations=model.max_iterations,
        is_completed=model.is_completed,
        output_json=_safe_json_dump(model.output_json),
        validation_is_valid=model.validation_is_valid,
        validation_errors=model.validation_errors,
        validation_error_messages=[str(m) for m in (model.validation_error_messages or [])],
        total_llm_calls=model.total_llm_calls,
        user_instructions=model.user_instructions,
        embedding=list(model.embedding) if model.embedding else None,
        embedding_model=model.embedding_model,
        reflection=model.reflection,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _model_to_summary(model: AgentSessionModel) -> AgentSessionSummary:
    return AgentSessionSummary(
        session_id=AgentMemoryId(model.id),
        project_id=ProjectId(model.project_id),
        session_type=model.session_type,
        phase=SpecPhase(model.phase),
        skill_name=model.skill_name,
        is_completed=model.is_completed,
        total_llm_calls=model.total_llm_calls,
        validation_errors=model.validation_errors,
        user_instructions=model.user_instructions,
        created_at=model.created_at,
    )


def _safe_json_dump(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, default=str)
    except (TypeError, ValueError):
        return str(value)
