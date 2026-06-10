from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker

from kosmo.contracts.sdd.discovery import DiscoveryDocument
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.requirements_document import RequirementsDocument
from kosmo.domain.sdd.document_converters import extract_discovery_from_document


class SqlAlchemyDocumentRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def save_view(self, resource_type: str, resource_id: str, document: dict) -> None:
        async with self._session_factory() as session:
            if resource_type == "project":
                from kosmo.infrastructure.persistence.postgres.models.project import ProjectModel

                stmt = (
                    ProjectModel.__table__.update()
                    .where(ProjectModel.id == resource_id)
                    .values(discovery_document=document)
                )
                await session.execute(stmt)
                await session.commit()
            elif resource_type == "feature":
                from kosmo.infrastructure.persistence.postgres.models.feature import FeatureModel

                stmt = (
                    FeatureModel.__table__.update()
                    .where(FeatureModel.id == resource_id)
                    .values(requirements_document=document)
                )
                await session.execute(stmt)
                await session.commit()

    async def get_view(self, resource_type: str, resource_id: str) -> dict | None:
        async with self._session_factory() as session:
            if resource_type == "project":
                from kosmo.infrastructure.persistence.postgres.models.project import ProjectModel

                from sqlalchemy import select

                result = await session.execute(
                    select(ProjectModel.discovery_document).where(ProjectModel.id == resource_id)
                )
                row = result.scalar_one_or_none()
                return row
            elif resource_type == "feature":
                from kosmo.infrastructure.persistence.postgres.models.feature import FeatureModel

                from sqlalchemy import select

                result = await session.execute(
                    select(FeatureModel.requirements_document).where(FeatureModel.id == resource_id)
                )
                row = result.scalar_one_or_none()
                return row
        return None

    async def save_clean_discovery(
        self, project_id: ProjectId, discovery: DiscoveryDocument
    ) -> None:
        async with self._session_factory() as session:
            from kosmo.infrastructure.persistence.postgres.models.project import ProjectModel

            stmt = (
                ProjectModel.__table__.update()
                .where(ProjectModel.id == str(project_id))
                .values(discovery_clean=discovery.model_dump())
            )
            await session.execute(stmt)
            await session.commit()

    async def get_clean_discovery(self, project_id: ProjectId) -> DiscoveryDocument | None:
        async with self._session_factory() as session:
            from kosmo.infrastructure.persistence.postgres.models.project import ProjectModel

            from sqlalchemy import select

            result = await session.execute(
                select(ProjectModel.discovery_clean).where(ProjectModel.id == str(project_id))
            )
            row = result.scalar_one_or_none()
            if row and isinstance(row, dict):
                try:
                    return DiscoveryDocument(**row)
                except (TypeError, ValueError):
                    return None
        return None

    async def save_clean_requirements(
        self, feature_id: FeatureId, requirements: RequirementsDocument
    ) -> None:
        async with self._session_factory() as session:
            from kosmo.infrastructure.persistence.postgres.models.feature import FeatureModel

            data: dict[str, Any] = {
                "ubiquitous": [r.model_dump() for r in requirements.ubiquitous],
                "event": [r.model_dump() for r in requirements.event],
                "state": [r.model_dump() for r in requirements.state],
                "optional": [r.model_dump() for r in requirements.optional],
                "unwanted": [r.model_dump() for r in requirements.unwanted],
                "complex": [r.model_dump() for r in requirements.complex],
            }
            stmt = (
                FeatureModel.__table__.update()
                .where(FeatureModel.id == str(feature_id))
                .values(requirements_clean=data)
            )
            await session.execute(stmt)
            await session.commit()

    async def get_clean_requirements(self, feature_id: FeatureId) -> RequirementsDocument | None:
        async with self._session_factory() as session:
            from kosmo.infrastructure.persistence.postgres.models.feature import FeatureModel

            from sqlalchemy import select

            result = await session.execute(
                select(FeatureModel.requirements_clean).where(FeatureModel.id == str(feature_id))
            )
            row = result.scalar_one_or_none()
            if row and isinstance(row, dict):
                try:
                    from kosmo.contracts.sdd.ears import EARSRequirement

                    def _parse_reqs(items: list, pattern: str) -> list[EARSRequirement]:
                        result_list: list[EARSRequirement] = []
                        for item in items:
                            if isinstance(item, dict):
                                try:
                                    result_list.append(EARSRequirement(**item))
                                except (TypeError, ValueError):
                                    pass
                        return result_list

                    return RequirementsDocument(
                        ubiquitous=_parse_reqs(row.get("ubiquitous", []), "ubiquitous"),
                        event=_parse_reqs(row.get("event", []), "event"),
                        state=_parse_reqs(row.get("state", []), "state"),
                        optional=_parse_reqs(row.get("optional", []), "optional"),
                        unwanted=_parse_reqs(row.get("unwanted", []), "unwanted"),
                        complex=_parse_reqs(row.get("complex", []), "complex"),
                    )
                except (TypeError, ValueError):
                    return None
        return None

    async def sync_clean_from_view(
        self, resource_type: str, resource_id: str
    ) -> DiscoveryDocument | RequirementsDocument | None:
        view = await self.get_view(resource_type, resource_id)
        if view is None:
            return None

        if resource_type == "project":
            discovery_dict = extract_discovery_from_document(view)
            discovery = DiscoveryDocument(**discovery_dict)
            await self.save_clean_discovery(ProjectId(resource_id), discovery)
            return discovery

        return None
