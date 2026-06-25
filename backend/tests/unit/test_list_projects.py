import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.application.projects.list_projects import ListProjectsUseCase
from kosmo.contracts.sdd.ids import ProjectId, UserId
from kosmo.contracts.sdd.project import Project


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


@pytest.mark.asyncio
async def test_list_projects_returns_empty_list_when_owner_has_no_projects() -> None:
    # Arrange
    repository: Any = InMemoryProjectRepository()
    use_case = ListProjectsUseCase(project_repository=repository)

    # Act
    result = await use_case.execute(owner_id=UserId("usr_123"))

    # Assert
    assert result == []


@pytest.mark.asyncio
async def test_list_projects_returns_only_projects_owned_by_user() -> None:
    # Arrange
    repository: Any = InMemoryProjectRepository()
    await repository.save(_make_project("prj_1", "proyecto-uno", "usr_123"))
    await repository.save(_make_project("prj_2", "proyecto-dos", "usr_123"))
    await repository.save(_make_project("prj_3", "ajeno", "usr_999"))
    use_case = ListProjectsUseCase(project_repository=repository)

    # Act
    result = await use_case.execute(owner_id=UserId("usr_123"))

    # Assert
    assert len(result) == 2
    assert {str(p.id) for p in result} == {"prj_1", "prj_2"}
    assert all(str(p.owner_id) == "usr_123" for p in result)


@pytest.mark.asyncio
async def test_list_projects_returns_all_projects_for_owner() -> None:
    # Arrange
    repository: Any = InMemoryProjectRepository()
    for index in range(3):
        await repository.save(_make_project(f"prj_{index}", f"proyecto-{index}", "usr_456"))
    use_case = ListProjectsUseCase(project_repository=repository)

    # Act
    result = await use_case.execute(owner_id=UserId("usr_456"))

    # Assert
    assert len(result) == 3
    assert {str(p.id) for p in result} == {"prj_0", "prj_1", "prj_2"}


@pytest.mark.asyncio
async def test_list_projects_accepts_userid_value_object() -> None:
    # Arrange
    repository: Any = InMemoryProjectRepository()
    await repository.save(_make_project("prj_1", "proyecto-uno", "usr_123"))
    use_case = ListProjectsUseCase(project_repository=repository)

    # Act
    result = await use_case.execute(owner_id=UserId("usr_123"))

    # Assert
    assert len(result) == 1
    assert str(result[0].owner_id) == "usr_123"
