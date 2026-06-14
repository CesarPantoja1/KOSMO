from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import FeatureRepository
from kosmo.infrastructure.persistence.postgres.models import FeatureModel


class SqlAlchemyFeatureRepository(FeatureRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def by_id(self, feature_id: FeatureId) -> Feature | None:
        async with self._session_factory() as session:
            model = await session.get(FeatureModel, str(feature_id))
            if model is None:
                return None
            return self._to_entity(model)

    async def list_by_project(self, project_id: ProjectId) -> list[Feature]:
        async with self._session_factory() as session:
            stmt = select(FeatureModel).where(FeatureModel.project_id == str(project_id))
            result = await session.execute(stmt)
            models = result.scalars().all()
            return [self._to_entity(m) for m in models]

    async def save(self, feature: Feature) -> Feature:
        async with self._session_factory() as session:
            model = await session.get(FeatureModel, str(feature.id))
            if model is None:
                model = self._to_model(feature)
                session.add(model)
            else:
                self._update_model(model, feature)
            await session.commit()
            return feature

    async def save_many(self, features: list[Feature]) -> list[Feature]:
        async with self._session_factory() as session:
            for feature in features:
                model = await session.get(FeatureModel, str(feature.id))
                if model is None:
                    session.add(self._to_model(feature))
                else:
                    self._update_model(model, feature)
            await session.commit()
            return features

    async def next_number(self, project_id: ProjectId) -> int:
        async with self._session_factory() as session:
            stmt = (
                select(FeatureModel.number)
                .where(FeatureModel.project_id == str(project_id))
                .order_by(FeatureModel.number.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            max_number = result.scalar_one_or_none()
            return (max_number or 0) + 1

    def _to_entity(self, model: FeatureModel) -> Feature:
        return Feature(
            id=FeatureId(model.id),
            project_id=ProjectId(model.project_id),
            number=model.number,
            title=model.title,
            slug=model.slug,
            description=model.description,
            rationale=model.rationale,
            inferred_from=model.inferred_from if isinstance(model.inferred_from, list) else [],
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, feature: Feature) -> FeatureModel:
        return FeatureModel(
            id=str(feature.id),
            project_id=str(feature.project_id),
            number=feature.number,
            title=feature.title,
            slug=feature.slug,
            description=feature.description,
            rationale=feature.rationale,
            inferred_from=feature.inferred_from,
        )

    def _update_model(self, model: FeatureModel, feature: Feature) -> None:
        model.number = feature.number
        model.title = feature.title
        model.slug = feature.slug
        model.description = feature.description
        model.rationale = feature.rationale
        model.inferred_from = feature.inferred_from
        model.updated_at = datetime.now(UTC)
