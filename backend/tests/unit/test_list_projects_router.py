from typing import Any

import pytest

from kosmo.application.projects.list_projects import ListProjectsUseCase
from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.ids import ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from kosmo.infrastructure.api.routers.projects import list_projects as list_projects_endpoint
from tests.unit.fakes import InMemoryProjectRepository


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
@pytest.mark.unit
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
