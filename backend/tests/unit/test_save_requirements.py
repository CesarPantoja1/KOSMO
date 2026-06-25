import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.application.requirements.save_requirements import SaveRequirementsUseCase
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
async def test_save_requirements_saves_markdown() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    feature_repo: Any = InMemoryFeatureRepository()
    requirement_repo: Any = InMemoryRequirementRepository()
    use_case = SaveRequirementsUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
    )

    project = Project(
        id=ProjectId("prj_req01"),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_01"),
    )
    await project_repo.save(project)

    feature = Feature(
        id=FeatureId("feat_req01"),
        number=1,
        title="Test Feature",
        slug="test-feature",
        description="Test feature description",
        project_id=project.id,
    )
    await feature_repo.save(feature)

    markdown = "## Requisitos EARS\n\n| ID | Categoría | Requisito |"
    project_id = ProjectId("prj_req01")
    feature_id = FeatureId("feat_req01")

    # Act
    await use_case.execute(project_id, feature_id, markdown)

    # Assert
    saved = await requirement_repo.by_feature_id(feature_id)
    assert saved is not None
    assert "Requisitos EARS" in saved


@pytest.mark.asyncio
async def test_save_requirements_raises_project_not_found() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    feature_repo: Any = InMemoryFeatureRepository()
    requirement_repo: Any = InMemoryRequirementRepository()
    use_case = SaveRequirementsUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
    )

    project_id = ProjectId("prj_nonexistent")
    feature_id = FeatureId("feat_req02")
    markdown = "## Requisitos"

    # Act & Assert
    with pytest.raises(ProjectNotFoundError):
        await use_case.execute(project_id, feature_id, markdown)


@pytest.mark.asyncio
async def test_save_requirements_raises_feature_not_found() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    feature_repo: Any = InMemoryFeatureRepository()
    requirement_repo: Any = InMemoryRequirementRepository()
    use_case = SaveRequirementsUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
    )

    project = Project(
        id=ProjectId("prj_req03"),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_03"),
    )
    await project_repo.save(project)

    project_id = ProjectId("prj_req03")
    feature_id = FeatureId("feat_nonexistent")
    markdown = "## Requisitos"

    # Act & Assert
    with pytest.raises(FeatureNotFoundError):
        await use_case.execute(project_id, feature_id, markdown)


@pytest.mark.asyncio
async def test_save_requirements_raises_feature_wrong_project() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    feature_repo: Any = InMemoryFeatureRepository()
    requirement_repo: Any = InMemoryRequirementRepository()
    use_case = SaveRequirementsUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
    )

    project_a = Project(
        id=ProjectId("prj_req04a"),
        name="Project A",
        slug="project-a",
        description="Test",
        owner_id=UserId("usr_04"),
    )
    project_b = Project(
        id=ProjectId("prj_req04b"),
        name="Project B",
        slug="project-b",
        description="Test",
        owner_id=UserId("usr_04"),
    )
    await project_repo.save(project_a)
    await project_repo.save(project_b)

    feature = Feature(
        id=FeatureId("feat_req04"),
        number=1,
        title="Feature",
        slug="feature",
        description="Feature belonging to project A",
        project_id=project_a.id,
    )
    await feature_repo.save(feature)

    project_id = ProjectId("prj_req04b")
    feature_id = FeatureId("feat_req04")
    markdown = "## Requisitos"

    # Act & Assert
    with pytest.raises(FeatureNotFoundError):
        await use_case.execute(project_id, feature_id, markdown)
