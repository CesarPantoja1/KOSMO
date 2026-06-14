from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.sdd.ids import FeatureId
from kosmo.contracts.sdd.repositories import RequirementRepository
from kosmo.infrastructure.persistence.postgres.models import RequirementModel


class SqlAlchemyRequirementRepository(RequirementRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def by_feature_id(self, feature_id: FeatureId) -> str | None:
        async with self._session_factory() as session:
            model = await session.get(RequirementModel, str(feature_id))
            if model is None:
                return None
            return model.markdown

    async def save(self, feature_id: FeatureId, markdown: str) -> None:
        async with self._session_factory() as session:
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
            await session.commit()

    async def save_many(self, *args: object) -> list:
        raise NotImplementedError

    async def next_requirement_number(self, *args: object) -> int:
        return 1
