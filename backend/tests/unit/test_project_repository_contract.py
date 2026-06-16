from dataclasses import dataclass

from kosmo.contracts.projects import ProjectId, Proyecto, ProyectoRepository, UserId


@dataclass(frozen=True, slots=True)
class FakeProyecto:
    id: ProjectId
    slug: str
    owner_id: UserId


class InMemoryProyectoRepository:
    def __init__(self) -> None:
        self.projects: dict[ProjectId, Proyecto] = {}

    async def save(self, project: Proyecto) -> Proyecto:
        self.projects[project.id] = project
        return project

    async def get_by_id(self, project_id: ProjectId) -> Proyecto | None:
        return self.projects.get(project_id)

    async def get_by_slug(self, slug: str) -> Proyecto | None:
        return next((project for project in self.projects.values() if project.slug == slug), None)

    async def list_by_owner(self, owner_id: UserId) -> list[Proyecto]:
        return [project for project in self.projects.values() if project.owner_id == owner_id]


async def test_proyecto_repository_protocol_defines_required_operations() -> None:
    repository: ProyectoRepository = InMemoryProyectoRepository()
    owner_id = UserId("usr_123")
    project = FakeProyecto(id=ProjectId("prj_123"), slug="mi-proyecto", owner_id=owner_id)

    saved = await repository.save(project)

    assert saved is project
    assert await repository.get_by_id(project.id) == project
    assert await repository.get_by_slug(project.slug) == project
    assert await repository.list_by_owner(owner_id) == [project]
