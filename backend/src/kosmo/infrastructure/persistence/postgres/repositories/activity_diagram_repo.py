from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kosmo.contracts.sdd.activity_diagram import DiagramaActividad
from kosmo.contracts.sdd.ids import ActivityDiagramId, FeatureId
from kosmo.contracts.sdd.repositories import ActivityDiagramRepository
from kosmo.infrastructure.persistence.postgres.models import ActivityDiagramModel


class SqlAlchemyActivityDiagramRepository(ActivityDiagramRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, diagram: DiagramaActividad) -> DiagramaActividad:
        stmt = select(ActivityDiagramModel).where(ActivityDiagramModel.id == diagram.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            model = ActivityDiagramModel(
                id=diagram.id,
                feature_id=diagram.feature_id,
                diagram_syntax=diagram.diagram_syntax,
                created_at=diagram.created_at,
                updated_at=diagram.updated_at,
            )
            self._session.add(model)
        else:
            model.feature_id = diagram.feature_id
            model.diagram_syntax = diagram.diagram_syntax
            model.updated_at = datetime.now(UTC)

        await self._session.flush()
        return diagram

    async def by_feature_id(self, feature_id: FeatureId) -> DiagramaActividad | None:
        stmt = select(ActivityDiagramModel).where(ActivityDiagramModel.feature_id == feature_id)
        result = await self._session.execute(stmt)
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
        stmt = select(ActivityDiagramModel.id).where(ActivityDiagramModel.feature_id == feature_id)
        result = await self._session.execute(stmt)
        return result.first() is not None
