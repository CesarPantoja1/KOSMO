from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.project import Project, ProjectPhase, ProjectStatus
from kosmo.infrastructure.persistence.postgres.models.project import ProjectModel


class SqlAlchemyProjectRepository:
    def __init__(self, session_factory: object) -> None:  # type: ignore[override]
        self._session_factory = session_factory  # type: ignore[assignment]

    async def add(self, project: Project) -> None:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            model = ProjectModel(  # type: ignore[call-arg]
                id=project.id,
                name=project.name,
                slug=project.slug,
                description=project.description,
                current_phase=project.current_phase.value,
                status=project.status.value,
                last_activity_at=project.last_activity_at,
                created_by=project.created_by,
                created_at=project.created_at,
                updated_at=project.updated_at,
                discovery_document=project.discovery_document,
            )
            session.add(model)
            await session.commit()

    async def get(self, project_id: ProjectId) -> Project | None:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            result = await session.execute(
                select(ProjectModel).where(ProjectModel.id == project_id)  # type: ignore[arg-type,union-attr]
            )
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return self._to_project(model)

    async def get_by_slug(self, slug: str) -> Project | None:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            result = await session.execute(
                select(ProjectModel).where(ProjectModel.slug == slug)  # type: ignore[arg-type,union-attr]
            )
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return self._to_project(model)

    async def list_all(self) -> list[Project]:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            result = await session.execute(
                select(ProjectModel).order_by(ProjectModel.updated_at.desc())  # type: ignore[arg-type,union-attr]
            )
            models = result.scalars().all()
            return [self._to_project(m) for m in models]

    async def update(self, project: Project) -> None:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            result = await session.execute(
                select(ProjectModel).where(ProjectModel.id == project.id)  # type: ignore[arg-type,union-attr]
            )
            model = result.scalar_one_or_none()
            if model is None:
                return
            model.name = project.name  # type: ignore[union-attr]
            model.description = project.description  # type: ignore[union-attr]
            model.current_phase = project.current_phase.value  # type: ignore[union-attr]
            model.status = project.status.value  # type: ignore[union-attr]
            model.last_activity_at = datetime.now(UTC)  # type: ignore[union-attr]
            model.updated_at = datetime.now(UTC)  # type: ignore[union-attr]
            await session.commit()

    async def update_discovery_document(
        self, project_id: ProjectId, document: dict[str, Any]
    ) -> None:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            await session.execute(
                sql_update(ProjectModel)
                .where(ProjectModel.id == project_id)  # type: ignore[arg-type,union-attr]
                .values(
                    discovery_document=document,
                    updated_at=datetime.now(UTC),
                    last_activity_at=datetime.now(UTC),
                )
            )
            await session.commit()

    async def get_discovery_document(self, project_id: ProjectId) -> dict[str, Any] | None:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            result = await session.execute(
                select(ProjectModel.discovery_document).where(
                    ProjectModel.id == project_id  # type: ignore[arg-type,union-attr]
                )
            )
            return result.scalar_one_or_none()

    @staticmethod
    def _to_project(model: object) -> Project:  # type: ignore[no-untyped-def]
        return Project(
            id=ProjectId(model.id),  # type: ignore[arg-type,union-attr]
            name=model.name,  # type: ignore[arg-type,union-attr]
            slug=model.slug,  # type: ignore[arg-type,union-attr]
            description=model.description,  # type: ignore[arg-type,union-attr]
            current_phase=ProjectPhase(model.current_phase),  # type: ignore[arg-type,union-attr]
            status=ProjectStatus(model.status),  # type: ignore[arg-type,union-attr]
            last_activity_at=model.last_activity_at,  # type: ignore[arg-type,union-attr]
            created_by=model.created_by,  # type: ignore[arg-type,union-attr]
            created_at=model.created_at,  # type: ignore[arg-type,union-attr]
            updated_at=model.updated_at,  # type: ignore[arg-type,union-attr]
            discovery_document=model.discovery_document,  # type: ignore[arg-type,union-attr]
        )
