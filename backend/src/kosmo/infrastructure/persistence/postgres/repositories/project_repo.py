from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.sdd.document import ProjectPhase, ProjectStatus
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.project import Project
from kosmo.contracts.sdd.repositories import ProjectRepository
from kosmo.infrastructure.persistence.postgres.models import ProjectModel


class SqlAlchemyProjectRepository(ProjectRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def by_id(self, project_id: ProjectId) -> Project | None:
        async with self._session_factory() as session:
            model = await session.get(ProjectModel, project_id)
            if model is None:
                return None
            return self._to_entity(model)

    async def by_slug(self, owner_id: str, slug: str) -> Project | None:
        async with self._session_factory() as session:
            from sqlalchemy import select

            stmt = (
                select(ProjectModel)
                .where(ProjectModel.owner_id == owner_id)
                .where(ProjectModel.slug == slug)
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return self._to_entity(model)

    async def find_by_slug(self, slug: str) -> Project | None:
        async with self._session_factory() as session:
            from sqlalchemy import select

            stmt = select(ProjectModel).where(ProjectModel.slug == slug)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return self._to_entity(model)

    async def list_by_owner(self, owner_id: str) -> list[Project]:
        async with self._session_factory() as session:
            from sqlalchemy import select

            stmt = select(ProjectModel).where(ProjectModel.owner_id == owner_id)
            result = await session.execute(stmt)
            models = result.scalars().all()
            return [self._to_entity(m) for m in models]

    async def save(self, project: Project) -> Project:
        async with self._session_factory() as session:
            model = await session.get(ProjectModel, str(project.id))
            if model is None:
                model = ProjectModel(
                    id=str(project.id),
                    name=project.name,
                    slug=project.slug,
                    description=project.description,
                    owner_id=str(project.owner_id),
                    current_phase=project.current_phase.value,
                    status=project.status.value,
                )
                session.add(model)
            else:
                model.name = project.name
                model.slug = project.slug
                model.description = project.description
                model.current_phase = project.current_phase.value
                model.status = project.status.value
                model.updated_at = datetime.now(UTC)
            await session.commit()
            return project

    async def update_phase(self, project_id: ProjectId, phase: ProjectPhase) -> Project | None:
        async with self._session_factory() as session:
            model = await session.get(ProjectModel, str(project_id))
            if model is None:
                return None
            model.current_phase = phase.value
            model.updated_at = datetime.now(UTC)
            await session.commit()
            return self._to_entity(model)

    async def update_status(self, project_id: ProjectId, status: ProjectStatus) -> Project | None:
        async with self._session_factory() as session:
            model = await session.get(ProjectModel, str(project_id))
            if model is None:
                return None
            model.status = status.value
            model.updated_at = datetime.now(UTC)
            await session.commit()
            return self._to_entity(model)

    def _to_entity(self, model: ProjectModel) -> Project:
        return Project(
            id=ProjectId(model.id),
            name=model.name,
            slug=model.slug,
            description=model.description,
            owner_id=model.owner_id,
            current_phase=ProjectPhase(model.current_phase),
            status=ProjectStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
