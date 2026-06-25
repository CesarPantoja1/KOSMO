import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.application.projects.create_project import CreateProjectUseCase
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


@pytest.mark.asyncio
async def test_create_project_generates_slug_from_name() -> None:
    # Arrange
    repository: Any = InMemoryProjectRepository()
    use_case = CreateProjectUseCase(project_repository=repository)

    # Act
    project = await use_case.execute(
        name="Mi Proyecto Increíble",
        description="Una descripción",
        owner_id=UserId("usr_123"),
    )

    # Assert
    assert project.name == "Mi Proyecto Increíble"
    assert project.slug == "mi-proyecto-increible"
    assert project.description == "Una descripción"
    assert str(project.owner_id) == "usr_123"
    assert str(project.id).startswith("prj_")


@pytest.mark.asyncio
async def test_create_project_saves_with_correct_fields() -> None:
    # Arrange
    repository: Any = InMemoryProjectRepository()
    use_case = CreateProjectUseCase(project_repository=repository)

    # Act
    project = await use_case.execute(
        name="Test Project",
        description="Test description",
        owner_id=UserId("usr_456"),
    )

    # Assert
    saved = await repository.by_id(project.id)
    assert saved is not None
    assert saved.name == "Test Project"
    assert saved.slug == "test-project"
    assert saved.description == "Test description"
    assert str(saved.owner_id) == "usr_456"


@pytest.mark.asyncio
async def test_create_project_handles_duplicate_slug_for_same_owner() -> None:
    # Arrange
    repository: Any = InMemoryProjectRepository()
    use_case = CreateProjectUseCase(project_repository=repository)

    # Act
    project1 = await use_case.execute(
        name="Mi Proyecto",
        description="Primer proyecto",
        owner_id=UserId("usr_123"),
    )
    project2 = await use_case.execute(
        name="Mi Proyecto",
        description="Segundo proyecto",
        owner_id=UserId("usr_123"),
    )

    # Assert
    assert project1.slug == "mi-proyecto"
    assert project2.slug == "mi-proyecto-2"
    assert project1.id != project2.id


@pytest.mark.asyncio
async def test_create_project_handles_special_characters_in_name() -> None:
    # Arrange
    repository: Any = InMemoryProjectRepository()
    use_case = CreateProjectUseCase(project_repository=repository)

    # Act
    project = await use_case.execute(
        name="Proyecto con Çaráctères!@#$%",
        description="Descripción",
        owner_id=UserId("usr_789"),
    )

    # Assert
    assert project.slug == "proyecto-con-caracteres"
