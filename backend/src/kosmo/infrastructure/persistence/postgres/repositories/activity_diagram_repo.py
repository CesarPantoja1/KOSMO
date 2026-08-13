from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.sdd.activity_diagram import DiagramaActividad
from kosmo.contracts.sdd.ids import ActivityDiagramId, FeatureId
from kosmo.contracts.sdd.repositories import ActivityDiagramRepository
from kosmo.infrastructure.persistence.postgres.models import ActivityDiagramModel


class SqlAlchemyActivityDiagramRepository(ActivityDiagramRepository):
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

    async def save(self, diagram: DiagramaActividad) -> DiagramaActividad:
        async with self._session_ctx() as session:
            stmt = select(ActivityDiagramModel).where(ActivityDiagramModel.feature_id == str(diagram.feature_id))
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                model = ActivityDiagramModel(
                    id=str(diagram.id),
                    feature_id=str(diagram.feature_id),
                    diagram_syntax=diagram.diagram_syntax,
                    created_at=diagram.created_at,
                    updated_at=diagram.updated_at,
                )
                session.add(model)
            else:
                model.feature_id = str(diagram.feature_id)
                model.diagram_syntax = diagram.diagram_syntax
                model.updated_at = datetime.now(UTC)

            await self._commit(session)
            return diagram

    async def by_feature_id(self, feature_id: FeatureId) -> DiagramaActividad | None:
        async with self._session_ctx() as session:
            stmt = select(ActivityDiagramModel).where(ActivityDiagramModel.feature_id == str(feature_id))
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                return None

            return DiagramaActividad(
                id=ActivityDiagramId(model.id),
                feature_id=FeatureId(model.feature_id),
                diagram_syntax=model.diagram_syntax,
                created_at=model.created_at,
                updated_at=model.updated_at,
            )

    async def exists(self, feature_id: FeatureId) -> bool:
        async with self._session_ctx() as session:
            stmt = select(ActivityDiagramModel.id).where(ActivityDiagramModel.feature_id == str(feature_id))
            result = await session.execute(stmt)
            return result.first() is not None
