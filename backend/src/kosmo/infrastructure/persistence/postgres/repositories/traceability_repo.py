from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.sdd.ids import FeatureId, RequirementId
from kosmo.domain.sdd.id_generator import IdGenerator
from kosmo.infrastructure.persistence.postgres.models import TraceabilityEdgeModel


class SqlAlchemyTraceabilityRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def add_edge(
        self,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        origin: str = "llm",
    ) -> None:
        async with self._session_factory() as session:
            model = TraceabilityEdgeModel(
                id=IdGenerator.generate("trace_edge"),
                source_type=source_type,
                source_id=source_id,
                target_type=target_type,
                target_id=target_id,
                origin=origin,
            )
            session.add(model)
            await session.commit()

    async def get_impact(self, artifact_id: str) -> dict[str, list[dict[str, str]]]:
        upstream: list[dict[str, str]] = []
        downstream: list[dict[str, str]] = []

        async with self._session_factory() as session:
            up_stmt = select(TraceabilityEdgeModel).where(
                TraceabilityEdgeModel.target_id == artifact_id
            )
            up_result = await session.execute(up_stmt)
            for edge in up_result.scalars().all():
                upstream.append({
                    "type": edge.source_type,
                    "id": edge.source_id,
                    "origin": edge.origin,
                })

            down_stmt = select(TraceabilityEdgeModel).where(
                TraceabilityEdgeModel.source_id == artifact_id
            )
            down_result = await session.execute(down_stmt)
            for edge in down_result.scalars().all():
                downstream.append({
                    "type": edge.target_type,
                    "id": edge.target_id,
                    "origin": edge.origin,
                })

        return {"upstream": upstream, "downstream": downstream}

    async def add_feature_requirement_edges(
        self, feature_id: FeatureId, requirement_ids: list[RequirementId]
    ) -> None:
        async with self._session_factory() as session:
            for req_id in requirement_ids:
                session.add(
                    TraceabilityEdgeModel(
                        id=IdGenerator.generate("trace_edge"),
                        source_type="feature",
                        source_id=str(feature_id),
                        target_type="requirement",
                        target_id=str(req_id),
                        origin="llm",
                    )
                )
            await session.commit()
