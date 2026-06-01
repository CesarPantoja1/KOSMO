from typing import Any

from sqlalchemy import delete, select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from kosmo.contracts.sdd.feature import Feature, FeatureStatus
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.requirements_document import RequirementsDocument
from kosmo.infrastructure.persistence.postgres.models.feature import FeatureModel


class SqlAlchemyFeatureRepository:
    def __init__(self, session_factory: object) -> None:  # type: ignore[override]
        self._session_factory = session_factory  # type: ignore[assignment]

    async def add(self, feature: Feature) -> None:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            model = FeatureModel(  # type: ignore[call-arg]
                id=feature.id,
                project_id=feature.project_id,
                title=feature.title,
                slug=feature.slug,
                description=feature.description,
                status=feature.status.value,
                requirements_data=feature.requirements.model_dump()
                if feature.requirements
                else None,
                requirements_document=feature.requirements_document,
                created_at=feature.created_at,
            )
            session.add(model)
            await session.commit()

    async def get_by_project(self, project_id: ProjectId) -> list[Feature]:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            result = await session.execute(
                select(FeatureModel)
                .where(FeatureModel.project_id == project_id)  # type: ignore[arg-type,union-attr]
                .order_by(FeatureModel.created_at)
            )
            models = result.scalars().all()
            return [self._to_feature(m) for m in models]

    async def get(self, feature_id: FeatureId) -> Feature | None:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            result = await session.execute(
                select(FeatureModel).where(FeatureModel.id == feature_id)  # type: ignore[arg-type,union-attr]
            )
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return self._to_feature(model)

    async def get_by_slug(self, project_id: ProjectId, slug: str) -> Feature | None:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            result = await session.execute(
                select(FeatureModel).where(
                    FeatureModel.project_id == project_id,  # type: ignore[arg-type,union-attr]
                    FeatureModel.slug == slug,  # type: ignore[arg-type,union-attr]
                )
            )
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return self._to_feature(model)

    async def delete(self, feature_id: FeatureId) -> None:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            await session.execute(
                delete(FeatureModel).where(FeatureModel.id == feature_id)  # type: ignore[arg-type,union-attr]
            )
            await session.commit()

    async def update(self, feature: Feature) -> None:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            result = await session.execute(
                select(FeatureModel).where(FeatureModel.id == feature.id)  # type: ignore[arg-type,union-attr]
            )
            model = result.scalar_one_or_none()
            if model is None:
                return
            model.title = feature.title  # type: ignore[union-attr]
            model.description = feature.description  # type: ignore[union-attr]
            model.status = feature.status.value  # type: ignore[union-attr]
            await session.commit()

    async def update_requirements(
        self, feature_id: FeatureId, requirements: RequirementsDocument
    ) -> None:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            result = await session.execute(
                select(FeatureModel).where(FeatureModel.id == feature_id)  # type: ignore[arg-type,union-attr]
            )
            model = result.scalar_one_or_none()
            if model is None:
                return
            model.requirements_data = requirements.model_dump()  # type: ignore[union-attr]
            await session.commit()

    async def update_requirements_document(
        self, feature_id: FeatureId, document: dict[str, Any]
    ) -> None:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            await session.execute(
                sql_update(FeatureModel)
                .where(FeatureModel.id == feature_id)  # type: ignore[arg-type,union-attr]
                .values(requirements_document=document)
            )
            await session.commit()

    async def get_requirements_document(self, feature_id: FeatureId) -> dict[str, Any] | None:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            result = await session.execute(
                select(FeatureModel.requirements_document).where(
                    FeatureModel.id == feature_id  # type: ignore[arg-type,union-attr]
                )
            )
            return result.scalar_one_or_none()

    @staticmethod
    def _to_feature(model: object) -> Feature:  # type: ignore[no-untyped-def]
        requirements: RequirementsDocument | None = None
        if model.requirements_data:  # type: ignore[union-attr]
            requirements = RequirementsDocument.model_validate(
                model.requirements_data  # type: ignore[union-attr]
            )

        return Feature(
            id=FeatureId(model.id),  # type: ignore[arg-type,union-attr]
            project_id=ProjectId(model.project_id),  # type: ignore[arg-type,union-attr]
            title=model.title,  # type: ignore[arg-type,union-attr]
            slug=model.slug,  # type: ignore[arg-type,union-attr]
            description=model.description,  # type: ignore[arg-type,union-attr]
            status=FeatureStatus(model.status),  # type: ignore[arg-type,union-attr]
            requirements=requirements,
            requirements_document=model.requirements_document,  # type: ignore[arg-type,union-attr]
            created_at=model.created_at,  # type: ignore[arg-type,union-attr]
        )
