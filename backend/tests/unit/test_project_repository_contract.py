from dataclasses import dataclass
from typing import NewType

from kosmo.contracts.sdd.repositories import ProjectRepository

ProjectId = NewType("ProjectId", str)


@dataclass(frozen=True, slots=True)
class FakeProject:
    id: ProjectId
    owner_id: str
    slug: str
    phase: str = "descubrimiento"
    status: str = "en_proceso"


class InMemoryProjectRepository:
    def __init__(self) -> None:
        self.projects: dict[ProjectId, FakeProject] = {}

    async def by_id(self, project_id: ProjectId) -> FakeProject | None:
        return self.projects.get(project_id)

    async def by_slug(self, owner_id: str, slug: str) -> FakeProject | None:
        return next(
            (
                project
                for project in self.projects.values()
                if project.owner_id == owner_id and project.slug == slug
            ),
            None,
        )

    async def find_by_slug(self, slug: str) -> FakeProject | None:
        return next((project for project in self.projects.values() if project.slug == slug), None)

    async def list_by_owner(self, owner_id: str) -> list[FakeProject]:
        return [project for project in self.projects.values() if project.owner_id == owner_id]

    async def save(self, project: FakeProject) -> FakeProject:
        self.projects[project.id] = project
        return project

    async def update_phase(self, project_id: ProjectId, phase: str) -> FakeProject | None:
        project = self.projects.get(project_id)
        if project is None:
            return None

        updated = FakeProject(
            id=project.id,
            owner_id=project.owner_id,
            slug=project.slug,
            phase=phase,
            status=project.status,
        )
        self.projects[project_id] = updated
        return updated

    async def update_status(self, project_id: ProjectId, status: str) -> FakeProject | None:
        project = self.projects.get(project_id)
        if project is None:
            return None

        updated = FakeProject(
            id=project.id,
            owner_id=project.owner_id,
            slug=project.slug,
            phase=project.phase,
            status=status,
        )
        self.projects[project_id] = updated
        return updated


async def test_project_repository_protocol_defines_required_operations() -> None:
    repository: ProjectRepository = InMemoryProjectRepository()
    project = FakeProject(id=ProjectId("prj_123"), owner_id="usr_123", slug="mi-proyecto")

    saved = await repository.save(project)

    assert saved is project
    assert await repository.by_id(project.id) == project
    assert await repository.by_slug(project.owner_id, project.slug) == project
    assert await repository.find_by_slug(project.slug) == project
    assert await repository.list_by_owner(project.owner_id) == [project]

    by_phase = await repository.update_phase(project.id, "requisitos")
    by_status = await repository.update_status(project.id, "finalizado")

    assert by_phase is not None and by_phase.phase == "requisitos"
    assert by_status is not None and by_status.status == "finalizado"
