import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.application.projects.list_projects import ListProjectsUseCase
from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.ids import ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from kosmo.infrastructure.api.routers.projects import list_projects as list_projects_endpoint
from kosmo.infrastructure.api.schemas import ProjectResponse


class InMemoryProjectRepository:
    def __init__(self) -> None:
        self.projects: dict[str, Project] = {}

    async def by_id(self, project_id: ProjectId) -> Project | None:
        return self.projects.get(str(project_id))

    async def by_slug(self, owner_id: str, slug: str) -> Project | None:
        return next(
            (p for p in self.projects.values() if str(p.owner_id) == owner_id and p.slug == slug),
            None,
        )

    async def find_by_slug(self, slug: str) -> Project | None:
        return next((p for p in self.projects.values() if p.slug == slug), None)

    async def list_by_owner(self, owner_id: str) -> list[Project]:
        return [p for p in self.projects.values() if str(p.owner_id) == owner_id]

    async def save(self, project: Project) -> Project:  # type: ignore[override]
        self.projects[str(project.id)] = project
        return project


def _make_project(project_id: str, slug: str, owner_id: str) -> Project:
    return Project(
        id=ProjectId(project_id),
        name=slug.replace("-", " ").title(),
        slug=slug,
        description="Una descripción",
        owner_id=UserId(owner_id),
    )


def _principal(subject: str) -> Principal:
    return Principal(subject=subject, scopes=frozenset({"*"}))


@pytest.mark.asyncio
async def test_list_projects_endpoint_returns_empty_list_when_owner_has_no_projects() -> None:
    # Arrange
    repository: Any = InMemoryProjectRepository()
    use_case = ListProjectsUseCase(project_repository=repository)

    # Act
    result = await list_projects_endpoint(principal=_principal("usr_123"), use_case=use_case)

    # Assert
    assert result == []


@pytest.mark.asyncio
async def test_list_projects_endpoint_returns_projects_of_authenticated_principal() -> None:
    # Arrange
    repository: Any = InMemoryProjectRepository()
    await repository.save(_make_project("prj_1", "proyecto-uno", "usr_123"))
    await repository.save(_make_project("prj_2", "proyecto-dos", "usr_123"))
    use_case = ListProjectsUseCase(project_repository=repository)

    # Act
    result = await list_projects_endpoint(principal=_principal("usr_123"), use_case=use_case)

    # Assert
    assert len(result) == 2
    assert all(isinstance(item, ProjectResponse) for item in result)
    assert {item.id for item in result} == {"prj_1", "prj_2"}
    assert all(item.owner_id == "usr_123" for item in result)


@pytest.mark.asyncio
async def test_list_projects_endpoint_excludes_projects_of_other_owners() -> None:
    # Arrange
    repository: Any = InMemoryProjectRepository()
    await repository.save(_make_project("prj_1", "propio", "usr_123"))
    await repository.save(_make_project("prj_2", "ajeno", "usr_999"))
    use_case = ListProjectsUseCase(project_repository=repository)

    # Act
    result = await list_projects_endpoint(principal=_principal("usr_123"), use_case=use_case)

    # Assert
    assert len(result) == 1
    assert result[0].id == "prj_1"


@pytest.mark.asyncio
async def test_list_projects_endpoint_maps_domain_project_to_response() -> None:
    # Arrange
    repository: Any = InMemoryProjectRepository()
    await repository.save(_make_project("prj_1", "proyecto-uno", "usr_123"))
    use_case = ListProjectsUseCase(project_repository=repository)

    # Act
    result = await list_projects_endpoint(principal=_principal("usr_123"), use_case=use_case)

    # Assert
    response = result[0]
    assert response.id == "prj_1"
    assert response.name == "Proyecto Uno"
    assert response.slug == "proyecto-uno"
    assert response.description == "Una descripción"
    assert response.owner_id == "usr_123"
