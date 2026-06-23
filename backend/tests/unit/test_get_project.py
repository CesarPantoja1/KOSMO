import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.application.projects.get_project import GetProjectUseCase
from kosmo.contracts.sdd.errors import ProjectNotFoundError
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
async def test_get_project_returns_project_when_exists() -> None:
    # Arrange
    repository: Any = InMemoryProjectRepository()
    project = Project(
        id=ProjectId("prj_test123"),
        name="Test Project",
        slug="test-project",
        description="A test project",
        owner_id=UserId("usr_123"),
    )
    await repository.save(project)
    use_case = GetProjectUseCase(project_repository=repository)

    # Act
    result = await use_case.execute(project_id=ProjectId("prj_test123"))

    # Assert
    assert result.id == ProjectId("prj_test123")
    assert result.name == "Test Project"
    assert result.slug == "test-project"
    assert str(result.owner_id) == "usr_123"


@pytest.mark.asyncio
async def test_get_project_raises_project_not_found_when_missing() -> None:
    # Arrange
    repository: Any = InMemoryProjectRepository()
    use_case = GetProjectUseCase(project_repository=repository)

    # Act & Assert
    with pytest.raises(ProjectNotFoundError) as exc_info:
        await use_case.execute(project_id=ProjectId("prj_nonexistent"))

    assert "prj_nonexistent" in str(exc_info.value.problem.detail)
    assert exc_info.value.problem.status == 404
