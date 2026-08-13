from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.sdd.ids import FeatureId
from kosmo.contracts.sdd.repositories import RequirementRepository
from kosmo.infrastructure.persistence.postgres.models import RequirementModel


class SqlAlchemyRequirementRepository(RequirementRepository):
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

    async def by_feature_id(self, feature_id: FeatureId) -> str | None:
        async with self._session_ctx() as session:
            model = await session.get(RequirementModel, str(feature_id))
            if model is None:
                return None
            return model.markdown

    async def save(self, feature_id: FeatureId, markdown: str) -> None:
        async with self._session_ctx() as session:
            model = await session.get(RequirementModel, str(feature_id))
            if model is None:
                model = RequirementModel(
                    feature_id=str(feature_id),
                    markdown=markdown,
                )
                session.add(model)
            else:
                model.markdown = markdown
                model.updated_at = datetime.now(UTC)
            await self._commit(session)

    async def save_many(self, *args: object) -> list[object]:
        raise NotImplementedError

    async def next_requirement_number(self, *args: object) -> int:  # noqa: ARG002
        return 1
