import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.application.requirements.generate_ears import GetRequirementsUseCase
from kosmo.contracts.sdd.errors import FeatureNotFoundError, ProjectNotFoundError
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId, UserId
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


class InMemoryFeatureRepository:
    def __init__(self) -> None:
        self.features: dict[str, Feature] = {}

    async def by_id(self, feature_id: FeatureId) -> Feature | None:
        return self.features.get(str(feature_id))

    async def list_by_project(self, project_id: ProjectId) -> list[Feature]:
        return [f for f in self.features.values() if str(f.project_id) == str(project_id)]

    async def save(self, feature: Feature) -> Feature:  # type: ignore[override]
        self.features[str(feature.id)] = feature
        return feature

    async def save_many(self, features: list[Feature]) -> list[Feature]:  # type: ignore[override]
        for f in features:
            self.features[str(f.id)] = f
        return features

    async def next_number(self, project_id: ProjectId) -> int:
        project_features = await self.list_by_project(project_id)
        return max((f.number for f in project_features), default=0) + 1


class InMemoryRequirementRepository:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    async def by_feature_id(self, feature_id: FeatureId) -> str | None:
        return self._data.get(str(feature_id))

    async def save(self, feature_id: FeatureId, markdown: str) -> None:
        self._data[str(feature_id)] = markdown


@pytest.mark.asyncio
async def test_get_requirements_returns_markdown_when_exists() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    feature_repo: Any = InMemoryFeatureRepository()
    requirement_repo: Any = InMemoryRequirementRepository()
    use_case = GetRequirementsUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
    )

    project = Project(
        id=ProjectId("prj_getreq01"),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_getreq01"),
    )
    await project_repo.save(project)

    feature = Feature(
        id=FeatureId("feat_getreq01"),
        number=1,
        title="Test Feature",
        slug="test-feature",
        description="Test feature",
        project_id=project.id,
    )
    await feature_repo.save(feature)

    markdown = "## Requisitos EARS\n\n| ID | Desc |"
    await requirement_repo.save(feature.id, markdown)

    project_id = ProjectId("prj_getreq01")
    feature_id = FeatureId("feat_getreq01")

    # Act
    result = await use_case.execute(project_id, feature_id)

    # Assert
    assert result is not None
    assert "Requisitos EARS" in result


@pytest.mark.asyncio
async def test_get_requirements_returns_none_when_not_exists() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    feature_repo: Any = InMemoryFeatureRepository()
    requirement_repo: Any = InMemoryRequirementRepository()
    use_case = GetRequirementsUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
    )

    project = Project(
        id=ProjectId("prj_getreq02"),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_getreq02"),
    )
    await project_repo.save(project)

    feature = Feature(
        id=FeatureId("feat_getreq02"),
        number=1,
        title="Test Feature",
        slug="test-feature",
        description="Test feature",
        project_id=project.id,
    )
    await feature_repo.save(feature)

    project_id = ProjectId("prj_getreq02")
    feature_id = FeatureId("feat_getreq02")

    # Act
    result = await use_case.execute(project_id, feature_id)

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_get_requirements_raises_project_not_found() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    feature_repo: Any = InMemoryFeatureRepository()
    requirement_repo: Any = InMemoryRequirementRepository()
    use_case = GetRequirementsUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
    )

    project_id = ProjectId("prj_nonexistent")
    feature_id = FeatureId("feat_getreq03")

    # Act & Assert
    with pytest.raises(ProjectNotFoundError):
        await use_case.execute(project_id, feature_id)


@pytest.mark.asyncio
async def test_get_requirements_raises_feature_not_found() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    feature_repo: Any = InMemoryFeatureRepository()
    requirement_repo: Any = InMemoryRequirementRepository()
    use_case = GetRequirementsUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
    )

    project = Project(
        id=ProjectId("prj_getreq04"),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_getreq04"),
    )
    await project_repo.save(project)

    project_id = ProjectId("prj_getreq04")
    feature_id = FeatureId("feat_nonexistent")

    # Act & Assert
    with pytest.raises(FeatureNotFoundError):
        await use_case.execute(project_id, feature_id)
