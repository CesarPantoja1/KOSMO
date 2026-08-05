from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.sdd.ids import FeatureId
from kosmo.contracts.sdd.repositories import RequirementRepository
from kosmo.infrastructure.persistence.postgres.models import RequirementItemModel, RequirementModel


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

    async def save_items(self, feature_id: FeatureId, items: list[object]) -> None:  # type: ignore[override]
        async with self._session_factory() as session:
            await session.execute(
                delete(RequirementItemModel).where(RequirementItemModel.feature_id == str(feature_id))
            )
            for item in items:
                data: dict[str, Any] = item if isinstance(item, dict) else item.__dict__  # type: ignore[reportUnknownVariableType]
                model = RequirementItemModel(
                    id=data.get("id", ""),
                    feature_id=str(feature_id),
                    requirement_number=int(data.get("requirement_number", 0)),
                    display_id=str(data.get("display_id", "")),
                    title=str(data.get("title", "")),
                    pattern=str(data.get("pattern", "")),
                    statement=str(data.get("statement", "")),
                    origin=str(data.get("origin", "")),
                    acceptance_criteria=(
                        list(data.get("acceptance_criteria", []))  # type: ignore[reportUnknownArgumentType]
                        if data.get("acceptance_criteria")
                        else []
                    ),
                )
                session.add(model)
            await session.commit()

    async def list_items(self, feature_id: FeatureId) -> list[object]:  # type: ignore[override]
        async with self._session_factory() as session:
            stmt = (
                select(RequirementItemModel)
                .where(RequirementItemModel.feature_id == str(feature_id))
                .order_by(RequirementItemModel.requirement_number)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def save_many(self, *args: object) -> list[object]:
        raise NotImplementedError

    async def next_requirement_number(self, *args: object) -> int:  # noqa: ARG002
        return 1
