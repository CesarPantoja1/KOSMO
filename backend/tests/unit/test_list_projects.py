from typing import Any

import pytest

from kosmo.application.projects.list_projects import ListProjectsUseCase
from kosmo.contracts.sdd.ids import ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from tests.unit.fakes import InMemoryProjectRepository


def _make_project(project_id: str, slug: str, owner_id: str) -> Project:
    return Project(
        id=ProjectId(project_id),
        name=slug.replace("-", " ").title(),
        slug=slug,
        description="Una descripción",
        owner_id=UserId(owner_id),
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_list_projects_returns_empty_list_when_owner_has_no_projects() -> None:
    # Arrange
    repository: Any = InMemoryProjectRepository()
    use_case = ListProjectsUseCase(project_repository=repository)

    # Act
    result = await use_case.execute(owner_id=UserId("usr_123"))

    # Assert
    assert result == []


@pytest.mark.asyncio
@pytest.mark.unit
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
